# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""AWS HealthLake MCP Server implementation."""

import argparse
import json
from .fhir_operations import MAX_SEARCH_COUNT, HealthLakeClient, validate_datastore_id
from .models import (
    CreateResourceRequest,
    DatastoreFilter,
    ExportJobConfig,
    ImportJobConfig,
    JobFilter,
    UpdateResourceRequest,
)
from botocore.exceptions import ClientError, NoCredentialsError
from datetime import datetime
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from mcp.types import CallToolResult, Resource, TextContent
from pydantic import AnyUrl, Field
from typing import Any, Dict, List, Optional


# Server configuration
SERVER_INSTRUCTIONS = """
# AWS HealthLake MCP Server

This MCP server provides tools for AWS HealthLake FHIR operations with comprehensive resource management capabilities.

## IMPORTANT: Use MCP Tools for HealthLake Operations

DO NOT use standard AWS CLI commands (aws healthlake). Always use the MCP tools provided by this server for HealthLake operations.

## Usage Notes

- By default, the server runs in read-only mode. Use the `--allow-write` flag to enable write operations.
- The server automatically discovers HealthLake datastores as MCP resources.
- All tools support comprehensive error handling with structured responses.
- Search operations support advanced FHIR search parameters including chaining, includes, and modifiers.

## Common Workflows

### Basic Resource Management
1. List datastores: `list_datastores()`
2. Get datastore details: `get_datastore_details(datastore_id='your-datastore-id')`
3. Create a resource: `create_fhir_resource(datastore_id='...', resource_type='Patient', resource_data={...})`
4. Read a resource: `read_fhir_resource(datastore_id='...', resource_type='Patient', resource_id='...')`
5. Update a resource: `update_fhir_resource(datastore_id='...', resource_type='Patient', resource_id='...', resource_data={...})`
6. Delete a resource: `delete_fhir_resource(datastore_id='...', resource_type='Patient', resource_id='...')`

### Advanced Search Operations
1. Basic search: `search_fhir_resources(datastore_id='...', resource_type='Patient', search_params={'name': 'Smith'})`
2. Advanced search with includes: `search_fhir_resources(datastore_id='...', resource_type='Patient', search_params={'name:contains': 'smith'}, include_params=['Patient:general-practitioner'])`
3. Patient everything: `patient_everything(datastore_id='...', patient_id='...', start='2023-01-01', end='2023-12-31')`

### Job Management
1. Start import job: `start_fhir_import_job(datastore_id='...', input_data_config={...}, job_output_data_config={...}, data_access_role_arn='...')`
2. Start export job: `start_fhir_export_job(datastore_id='...', output_data_config={...}, data_access_role_arn='...')`
3. List jobs: `list_fhir_jobs(datastore_id='...', job_status='COMPLETED', job_type='IMPORT')`

## Best Practices

- Use descriptive resource names and proper FHIR resource structures.
- Leverage the automatic datastore discovery through MCP resources.
- Use advanced search parameters for efficient data retrieval.
- Monitor job status when performing import/export operations.
- Follow FHIR R4 specifications for resource structures.
"""

SERVER_DEPENDENCIES = [
    'pydantic',
    'loguru',
    'boto3',
    'botocore',
]


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime objects."""

    def default(self, o):
        """Convert datetime objects to ISO format strings."""
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)


class InputValidationError(Exception):
    """Custom validation error for input parameters."""

    pass


def validate_count(count: int) -> int:
    """Validate and normalize count parameter."""
    if count < 1 or count > MAX_SEARCH_COUNT:
        raise InputValidationError(f'Count must be between 1 and {MAX_SEARCH_COUNT}')
    return count


def create_error_response(message: str, error_type: str = 'error') -> CallToolResult:
    """Create standardized error response."""
    return CallToolResult(
        isError=True,
        content=[
            TextContent(
                type='text',
                text=json.dumps({'error': True, 'type': error_type, 'message': message}, indent=2),
            )
        ],
    )


def create_success_response(data: Any) -> CallToolResult:
    """Create standardized success response."""
    return CallToolResult(
        content=[TextContent(type='text', text=json.dumps(data, indent=2, cls=DateTimeEncoder))]
    )


class HealthLakeHandler:
    """Handler for HealthLake operations in the MCP Server."""

    def __init__(self, mcp: FastMCP, read_only: bool = False):
        """Initialize the HealthLake handler.

        Args:
            mcp: The FastMCP server instance
            read_only: Whether to enable read-only mode (default: False)
        """
        self.mcp = mcp
        self.client = HealthLakeClient()
        self.read_only = read_only

        # Register all tools
        self._register_tools()

        # Register resources
        self.mcp.resource('healthlake://datastore/{datastore_id}')(self._read_datastore_resource)

    def _register_tools(self):
        """Register all HealthLake tools with the MCP server."""
        # Datastore management tools (always available)
        self.mcp.tool(name='list_datastores')(self.list_datastores)
        self.mcp.tool(name='get_datastore_details')(self.get_datastore_details)

        # Read-only FHIR operations (always available)
        self.mcp.tool(name='read_fhir_resource')(self.read_fhir_resource)
        self.mcp.tool(name='search_fhir_resources')(self.search_fhir_resources)
        self.mcp.tool(name='patient_everything')(self.patient_everything)
        self.mcp.tool(name='list_fhir_jobs')(self.list_fhir_jobs)

        # Write operations (only if not read-only)
        if not self.read_only:
            self.mcp.tool(name='create_fhir_resource')(self.create_fhir_resource)
            self.mcp.tool(name='update_fhir_resource')(self.update_fhir_resource)
            self.mcp.tool(name='delete_fhir_resource')(self.delete_fhir_resource)
            self.mcp.tool(name='start_fhir_import_job')(self.start_fhir_import_job)
            self.mcp.tool(name='start_fhir_export_job')(self.start_fhir_export_job)

    def _check_write_access(self, operation_name: str) -> None:
        """Check if write access is allowed for the given operation."""
        if self.read_only:
            raise ValueError(
                f'Operation {operation_name} not available in read-only mode. '
                'Remove --readonly flag to enable write operations.'
            )

    async def _read_datastore_resource(self, uri: AnyUrl) -> str:
        """Read detailed datastore information."""
        uri_str = str(uri)
        if not uri_str.startswith('healthlake://datastore/'):
            raise ValueError(f'Unknown resource URI: {uri_str}')
        datastore_id = uri_str.split('/')[-1]
        result = await self.client.get_datastore_details(datastore_id)
        return json.dumps(result, indent=2, cls=DateTimeEncoder)

    async def list_datastores(
        self,
        ctx: Context,
        status: Optional[str] = Field(
            None,
            description='Filter datastores by status (CREATING, ACTIVE, DELETING, DELETED)',
        ),
    ) -> CallToolResult:
        """List all HealthLake datastores in the account."""
        try:
            filter_obj = DatastoreFilter(status=status)
            result = await self.client.list_datastores(filter_status=filter_obj.status)
            return create_success_response(result)
        except Exception as e:
            logger.error(f'Error listing datastores: {e}')
            return self._handle_error(e, 'list_datastores')

    async def get_datastore_details(
        self,
        ctx: Context,
        datastore_id: str = Field(..., description='HealthLake datastore ID'),
    ) -> CallToolResult:
        """Get detailed information about a specific HealthLake datastore."""
        try:
            datastore_id = validate_datastore_id(datastore_id)
            result = await self.client.get_datastore_details(datastore_id=datastore_id)
            return create_success_response(result)
        except Exception as e:
            logger.error(f'Error getting datastore details: {e}')
            return self._handle_error(e, 'get_datastore_details')

    async def create_fhir_resource(
        self,
        ctx: Context,
        datastore_id: str = Field(..., description='HealthLake datastore ID'),
        resource_type: str = Field(..., description='FHIR resource type'),
        resource_data: Dict[str, Any] = Field(
            ..., description='FHIR resource data as JSON object'
        ),
    ) -> CallToolResult:
        """Create a new FHIR resource in HealthLake."""
        try:
            self._check_write_access('create_fhir_resource')
            request = CreateResourceRequest(
                datastore_id=datastore_id, resource_type=resource_type, resource_data=resource_data
            )
            result = await self.client.create_resource(
                datastore_id=request.datastore_id,
                resource_type=request.resource_type,
                resource_data=request.resource_data,
            )
            return create_success_response(result)
        except Exception as e:
            logger.error(f'Error creating FHIR resource: {e}')
            return self._handle_error(e, 'create_fhir_resource')

    async def read_fhir_resource(
        self,
        ctx: Context,
        datastore_id: str = Field(..., description='HealthLake datastore ID'),
        resource_type: str = Field(..., description='FHIR resource type'),
        resource_id: str = Field(..., description='FHIR resource ID'),
    ) -> CallToolResult:
        """Get a specific FHIR resource by ID."""
        try:
            datastore_id = validate_datastore_id(datastore_id)
            result = await self.client.read_resource(
                datastore_id=datastore_id, resource_type=resource_type, resource_id=resource_id
            )
            return create_success_response(result)
        except Exception as e:
            logger.error(f'Error reading FHIR resource: {e}')
            return self._handle_error(e, 'read_fhir_resource')

    async def update_fhir_resource(
        self,
        ctx: Context,
        datastore_id: str = Field(..., description='HealthLake datastore ID'),
        resource_type: str = Field(..., description='FHIR resource type'),
        resource_id: str = Field(..., description='FHIR resource ID'),
        resource_data: Dict[str, Any] = Field(
            ..., description='Updated FHIR resource data as JSON object'
        ),
    ) -> CallToolResult:
        """Update an existing FHIR resource in HealthLake."""
        try:
            self._check_write_access('update_fhir_resource')
            request = UpdateResourceRequest(
                datastore_id=datastore_id,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_data=resource_data,
            )
            result = await self.client.update_resource(
                datastore_id=request.datastore_id,
                resource_type=request.resource_type,
                resource_id=request.resource_id,
                resource_data=request.resource_data,
            )
            return create_success_response(result)
        except Exception as e:
            logger.error(f'Error updating FHIR resource: {e}')
            return self._handle_error(e, 'update_fhir_resource')

    async def delete_fhir_resource(
        self,
        ctx: Context,
        datastore_id: str = Field(..., description='HealthLake datastore ID'),
        resource_type: str = Field(..., description='FHIR resource type'),
        resource_id: str = Field(..., description='FHIR resource ID'),
    ) -> CallToolResult:
        """Delete a FHIR resource from HealthLake."""
        try:
            self._check_write_access('delete_fhir_resource')
            datastore_id = validate_datastore_id(datastore_id)
            result = await self.client.delete_resource(
                datastore_id=datastore_id, resource_type=resource_type, resource_id=resource_id
            )
            return create_success_response(result)
        except Exception as e:
            logger.error(f'Error deleting FHIR resource: {e}')
            return self._handle_error(e, 'delete_fhir_resource')

    async def search_fhir_resources(
        self,
        ctx: Context,
        datastore_id: str = Field(..., description='HealthLake datastore ID'),
        resource_type: str = Field(
            ..., description='FHIR resource type (e.g., Patient, Observation, Condition)'
        ),
        search_params: Optional[Dict[str, Any]] = Field(
            None,
            description="Basic FHIR search parameters. Supports modifiers (e.g., 'name:contains'), prefixes (e.g., 'birthdate': 'ge1990-01-01'), and simple chaining (e.g., 'subject:Patient')",
        ),
        chained_params: Optional[Dict[str, str]] = Field(
            None,
            description="Advanced chained search parameters. Key format: 'param.chain' or 'param:TargetType.chain' (e.g., {'subject.name': 'Smith', 'general-practitioner:Practitioner.name': 'Johnson'})",
        ),
        include_params: Optional[List[str]] = Field(
            None,
            description="Include related resources in the response. Format: 'ResourceType:parameter' or 'ResourceType:parameter:target-type' (e.g., ['Patient:general-practitioner', 'Observation:subject:Patient'])",
        ),
        revinclude_params: Optional[List[str]] = Field(
            None,
            description="Include resources that reference the found resources. Format: 'ResourceType:parameter' (e.g., ['Observation:subject', 'Condition:subject'])",
        ),
        count: int = Field(
            100,
            description='Maximum number of results to return (1-100, default: 100)',
            ge=1,
            le=100,
        ),
        next_token: Optional[str] = Field(
            None,
            description="Pagination token for retrieving the next page of results. Use the complete URL from a previous response's pagination.next_token field. When provided, other search parameters are ignored.",
        ),
    ) -> CallToolResult:
        """Search for FHIR resources in HealthLake datastore with advanced search capabilities."""
        try:
            datastore_id = validate_datastore_id(datastore_id)
            count = validate_count(count)
            result = await self.client.search_resources(
                datastore_id=datastore_id,
                resource_type=resource_type,
                search_params=search_params or {},
                include_params=include_params,
                revinclude_params=revinclude_params,
                chained_params=chained_params,
                count=count,
                next_token=next_token,
            )
            return create_success_response(result)
        except Exception as e:
            logger.error(f'Error searching FHIR resources: {e}')
            return self._handle_error(e, 'search_fhir_resources')

    async def patient_everything(
        self,
        ctx: Context,
        datastore_id: str = Field(..., description='HealthLake datastore ID'),
        patient_id: str = Field(..., description='Patient resource ID'),
        start: Optional[str] = Field(
            None, description='Start date for filtering resources (YYYY-MM-DD format)'
        ),
        end: Optional[str] = Field(
            None, description='End date for filtering resources (YYYY-MM-DD format)'
        ),
        count: int = Field(
            100,
            description='Maximum number of results to return (1-100, default: 100)',
            ge=1,
            le=100,
        ),
        next_token: Optional[str] = Field(
            None,
            description="Pagination token for retrieving the next page of results. Use the complete URL from a previous response's pagination.next_token field.",
        ),
    ) -> CallToolResult:
        """Retrieve all resources related to a specific patient using the FHIR $patient-everything operation."""
        try:
            datastore_id = validate_datastore_id(datastore_id)
            count = validate_count(count)
            result = await self.client.patient_everything(
                datastore_id=datastore_id,
                patient_id=patient_id,
                start=start,
                end=end,
                count=count,
                next_token=next_token,
            )
            return create_success_response(result)
        except Exception as e:
            logger.error(f'Error getting patient everything: {e}')
            return self._handle_error(e, 'patient_everything')

    async def start_fhir_import_job(
        self,
        ctx: Context,
        datastore_id: str = Field(..., description='HealthLake datastore ID'),
        input_data_config: Dict[str, Any] = Field(..., description='Input data configuration'),
        job_output_data_config: Dict[str, Any] = Field(
            ..., description='Output data configuration (required for import jobs)'
        ),
        data_access_role_arn: str = Field(..., description='IAM role ARN for data access'),
        job_name: Optional[str] = Field(None, description='Name for the import job'),
    ) -> CallToolResult:
        """Start a FHIR import job to load data into HealthLake."""
        try:
            self._check_write_access('start_fhir_import_job')
            request = ImportJobConfig(
                datastore_id=datastore_id,
                input_data_config=input_data_config,
                data_access_role_arn=data_access_role_arn,
                job_name=job_name,
            )
            result = await self.client.start_import_job(
                datastore_id=request.datastore_id,
                input_data_config=request.input_data_config,
                job_output_data_config=job_output_data_config,
                data_access_role_arn=request.data_access_role_arn,
                job_name=request.job_name,
            )
            return create_success_response(result)
        except Exception as e:
            logger.error(f'Error starting import job: {e}')
            return self._handle_error(e, 'start_fhir_import_job')

    async def start_fhir_export_job(
        self,
        ctx: Context,
        datastore_id: str = Field(..., description='HealthLake datastore ID'),
        output_data_config: Dict[str, Any] = Field(..., description='Output data configuration'),
        data_access_role_arn: str = Field(..., description='IAM role ARN for data access'),
        job_name: Optional[str] = Field(None, description='Name for the export job'),
    ) -> CallToolResult:
        """Start a FHIR export job to export data from HealthLake."""
        try:
            self._check_write_access('start_fhir_export_job')
            request = ExportJobConfig(
                datastore_id=datastore_id,
                output_data_config=output_data_config,
                data_access_role_arn=data_access_role_arn,
                job_name=job_name,
            )
            result = await self.client.start_export_job(
                datastore_id=request.datastore_id,
                output_data_config=request.output_data_config,
                data_access_role_arn=request.data_access_role_arn,
                job_name=request.job_name,
            )
            return create_success_response(result)
        except Exception as e:
            logger.error(f'Error starting export job: {e}')
            return self._handle_error(e, 'start_fhir_export_job')

    async def list_fhir_jobs(
        self,
        ctx: Context,
        datastore_id: str = Field(..., description='HealthLake datastore ID'),
        job_status: Optional[str] = Field(
            None,
            description='Filter jobs by status (SUBMITTED, IN_PROGRESS, COMPLETED, FAILED, STOP_REQUESTED, STOPPED)',
        ),
        job_type: Optional[str] = Field(None, description='Type of job to list (IMPORT, EXPORT)'),
    ) -> CallToolResult:
        """List FHIR import/export jobs."""
        try:
            datastore_id = validate_datastore_id(datastore_id)
            filter_obj = JobFilter(job_status=job_status, job_type=job_type)
            result = await self.client.list_jobs(
                datastore_id=datastore_id,
                job_status=filter_obj.job_status,
                job_type=filter_obj.job_type,
            )
            return create_success_response(result)
        except Exception as e:
            logger.error(f'Error listing jobs: {e}')
            return self._handle_error(e, 'list_fhir_jobs')

    def _handle_error(self, error: Exception, tool_name: str) -> CallToolResult:
        """Handle errors and return appropriate error responses."""
        if isinstance(error, (InputValidationError, ValueError)):
            if 'read-only mode' in str(error):
                logger.warning(f'Read-only mode violation attempt: {tool_name}')
                return create_error_response(str(error), 'read_only_violation')
            else:
                logger.warning(f'Validation error in {tool_name}: {error}')
                return create_error_response(str(error), 'validation_error')
        elif isinstance(error, ClientError):
            error_code = error.response['Error']['Code']
            logger.error(f'AWS error in {tool_name}: {error_code}')
            errors = {
                'ResourceNotFoundException': ('Resource not found', 'not_found'),
                'ValidationException': (
                    f'Invalid parameters: {error.response["Error"]["Message"]}',
                    'validation_error',
                ),
            }
            msg, typ = errors.get(error_code, ('AWS service error', 'service_error'))
            return create_error_response(msg, typ)
        elif isinstance(error, NoCredentialsError):
            logger.error(f'Credentials error in {tool_name}')
            return create_error_response('AWS credentials not configured', 'auth_error')
        else:
            logger.exception('Unexpected error in tool call', tool=tool_name)
            return create_error_response('Internal server error', 'server_error')


def create_server():
    """Create and configure the MCP server instance."""
    return FastMCP(
        'awslabs.healthlake-mcp-server',
        instructions=SERVER_INSTRUCTIONS,
        dependencies=SERVER_DEPENDENCIES,
    )


def create_healthlake_server(read_only: bool = False) -> FastMCP:
    """Create and configure the HealthLake MCP server."""
    mcp = create_server()

    # Initialize handler
    HealthLakeHandler(mcp, read_only=read_only)

    # Register resources handler
    @mcp.list_resources()
    async def list_resources() -> List[Resource]:
        """List available HealthLake datastores as discoverable resources."""
        try:
            healthlake_client = HealthLakeClient()
            response = await healthlake_client.list_datastores()
            return [
                Resource(
                    uri=AnyUrl(f'healthlake://datastore/{ds["DatastoreId"]}'),
                    name=f'{"✅" if ds["DatastoreStatus"] == "ACTIVE" else "⏳"} {ds.get("DatastoreName", "Unnamed")} ({ds["DatastoreStatus"]})',
                    description=f'FHIR {ds["DatastoreTypeVersion"]} datastore\nCreated: {ds["CreatedAt"].strftime("%Y-%m-%d")}\nEndpoint: {ds["DatastoreEndpoint"]}\nID: {ds["DatastoreId"]}',
                    mimeType='application/json',
                )
                for ds in response.get('DatastorePropertiesList', [])
            ]
        except Exception as e:
            logger.error(f'Error listing datastore resources: {e}')
            return []

    return mcp


def main():
    """Run the MCP server with CLI argument support."""
    parser = argparse.ArgumentParser(
        description='An AWS Labs Model Context Protocol (MCP) server for HealthLake'
    )
    parser.add_argument(
        '--readonly',
        action='store_true',
        help='Enable read-only mode (blocks all mutating operations)',
    )

    args = parser.parse_args()

    # Log startup mode
    if args.readonly:
        logger.info('Starting HealthLake MCP Server in read-only mode')
    else:
        logger.info('Starting HealthLake MCP Server with write access enabled')

    # Create and run the server
    mcp = create_healthlake_server(read_only=args.readonly)
    mcp.run()

    return mcp


if __name__ == '__main__':
    main()
