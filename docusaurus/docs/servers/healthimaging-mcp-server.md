# AWS HealthImaging MCP Server

A comprehensive Model Context Protocol (MCP) server for AWS HealthImaging operations. Provides **39 tools** for complete medical imaging data lifecycle management with automatic datastore discovery and advanced DICOM operations.

## Features

- **39 Comprehensive HealthImaging Tools**: Complete medical imaging data lifecycle management
- **21 Standard AWS API Operations**: Full AWS HealthImaging API coverage including datastore management, import/export jobs, image sets, metadata, and resource tagging
- **18 Advanced DICOM Operations**: Specialized medical imaging workflows including patient/study/series level operations, bulk operations, and DICOM hierarchy management
- **Delete Operations**: Patient data removal, study deletion, supports compliance with "right to be forgotten/right to erasure" GDPR objectives
- **Metadata Updates**: Patient corrections, study modifications, series/instance management
- **Enhanced Search**: Patient-focused, study-focused, and series-focused searches with DICOM-aware filtering
- **Data Analysis**: Patient studies overview, series analysis, primary image set filtering, DICOMweb integration
- **Bulk Operations**: Efficient large-scale metadata updates and deletions with safety limits
- **DICOM Hierarchy Operations**: Series and instance removal with deep DICOM knowledge
- **Import/Export Jobs**: Complete DICOM data import and export workflow management
- **Automatic Datastore Discovery**: Seamlessly find and work with existing datastores
- **DICOM Metadata Operations**: Extract and analyze medical imaging metadata with base64 encoding for binary data
- **Image Frame Management**: Retrieve and process individual image frames
- **AWS Integration**: SigV4 authentication with automatic credential handling
- **Error Handling**: Structured error responses with specific error types
- **Docker Support**: Production-ready containerization
- **Type Safety**: Comprehensive Pydantic models for all operations

## Quick Start

### Option 1: uvx (Recommended)

```bash
uvx awslabs.healthimaging-mcp-server@latest
```

### Option 2: uv install

```bash
uv add awslabs.healthimaging-mcp-server
```

### Option 3: Docker

```bash
docker run -it --rm \
  -e AWS_REGION=us-east-1 \
  -e AWS_PROFILE=your-profile \
  -v ~/.aws:/root/.aws:ro \
  public.ecr.aws/awslabs/healthimaging-mcp-server:latest
```

## MCP Client Configuration

### Amazon Q Developer CLI

```json
{
  "mcpServers": {
    "healthimaging": {
      "command": "uvx",
      "args": ["awslabs.healthimaging-mcp-server@latest"],
      "env": {
        "AWS_REGION": "us-east-1",
        "AWS_PROFILE": "your-profile",
        "FASTMCP_LOG_LEVEL": "WARNING"
      }
    }
  }
}
```

### Other MCP Clients

For other MCP clients like Claude Desktop, add this to your configuration:

```json
{
  "mcpServers": {
    "healthimaging": {
      "command": "uvx",
      "args": ["awslabs.healthimaging-mcp-server@latest"],
      "env": {
        "AWS_REGION": "us-east-1",
        "AWS_PROFILE": "your-profile"
      }
    }
  }
}
```

## Available Tools

### Datastore Management (4 tools)
- `create_datastore` - Create new datastore with encryption options
- `delete_datastore` - Delete datastore (with safety checks)
- `get_datastore` - Get detailed datastore information and endpoints
- `list_datastores` - Discover available datastores with status filtering

### Image Set Operations (7 tools)
- `search_image_sets` - Advanced DICOM search with pagination
- `get_image_set` - Individual image set metadata
- `get_image_set_metadata` - Detailed DICOM metadata extraction with base64 encoding
- `list_image_set_versions` - Version history management
- `update_image_set_metadata` - DICOM metadata corrections
- `delete_image_set` - Individual image set deletion
- `copy_image_set` - Copy image sets between datastores

### Image Frame Operations (1 tool)
- `get_image_frame` - Frame-level access with base64 encoding

### DICOM Import/Export Jobs (6 tools)
- `start_dicom_import_job` - Start new import jobs
- `get_dicom_import_job` - Get import job details and status
- `list_dicom_import_jobs` - List import job status with filtering
- `start_dicom_export_job` - Start new export jobs
- `get_dicom_export_job` - Get export job details and status
- `list_dicom_export_jobs` - List export job status with filtering

### Resource Tagging (3 tools)
- `list_tags_for_resource` - List tags for HealthImaging resources
- `tag_resource` - Add tags to resources
- `untag_resource` - Remove tags from resources

### Enhanced Search Operations (3 tools)
- `search_by_patient_id` - Patient-focused clinical workflows
- `search_by_study_uid` - Study-centric analysis
- `search_by_series_uid` - Series-level investigations

### Data Analysis Operations (3 tools)
- `get_patient_studies` - Comprehensive patient study overview
- `get_patient_series` - Series-level analysis for patients
- `get_study_primary_image_sets` - Primary data identification

### Delete Operations (5 tools)
- `delete_patient_studies` - Complete patient data removal
- `delete_study` - Study-level deletion by UID
- `delete_series_by_uid` - Series deletion using metadata updates
- `delete_instance_in_study` - Delete specific instance in study
- `delete_instance_in_series` - Delete specific instance in series

### Metadata Update Operations (3 tools)
- `get_series_primary_image_set` - Get primary image set for series
- `get_patient_dicomweb_studies` - Get DICOMweb study-level info
- `update_patient_study_metadata` - Update Patient/Study metadata

### Bulk Operations (2 tools)
- `bulk_update_patient_metadata` - Mass patient data corrections
- `bulk_delete_by_criteria` - Criteria-based bulk deletion

### DICOM Hierarchy Operations (2 tools)
- `remove_series_from_image_set` - Series-level data management
- `remove_instance_from_image_set` - Instance-level precision removal

## Usage Examples

### Basic Operations

```python
# List all datastores
datastores = await list_datastores()

# Get specific datastore
datastore = await get_datastore(datastore_id="12345678901234567890123456789012")

# Search for image sets
results = await search_image_sets(
    datastore_id="12345678901234567890123456789012",
    search_criteria={
        "filters": [
            {
                "values": [{"DICOMPatientId": "PATIENT123"}],
                "operator": "EQUAL"
            }
        ]
    }
)
```

### Advanced DICOM Operations

```python
# Delete all studies for a patient
await delete_patient_studies(
    datastore_id="12345678901234567890123456789012",
    patient_id="PATIENT123"
)

# Get comprehensive patient study overview
studies = await get_patient_studies(
    datastore_id="12345678901234567890123456789012",
    patient_id="PATIENT123"
)

# Bulk update patient metadata
await bulk_update_patient_metadata(
    datastore_id="12345678901234567890123456789012",
    patient_id="PATIENT123",
    metadata_updates={"PatientName": "Updated Name"}
)
```

### Advanced Search

```python
# Complex search with multiple filters
results = await search_image_sets(
    datastore_id="12345678901234567890123456789012",
    search_criteria={
        "filters": [
            {
                "values": [{"DICOMStudyDate": "20240101"}],
                "operator": "EQUAL"
            },
            {
                "values": [{"DICOMModality": "CT"}],
                "operator": "EQUAL"
            }
        ]
    },
    max_results=50
)
```

### DICOM Metadata

```python
# Get DICOM metadata for an image set
metadata = await get_image_set_metadata(
    datastore_id="12345678901234567890123456789012",
    image_set_id="98765432109876543210987654321098"
)

# Get specific image frame
frame = await get_image_frame(
    datastore_id="12345678901234567890123456789012",
    image_set_id="98765432109876543210987654321098",
    image_frame_information={
        "imageFrameId": "frame123"
    }
)
```

## Authentication

### Required Permissions

Your AWS credentials need the following permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "medical-imaging:ListDatastores",
                "medical-imaging:GetDatastore",
                "medical-imaging:CreateDatastore",
                "medical-imaging:DeleteDatastore",
                "medical-imaging:SearchImageSets",
                "medical-imaging:GetImageSet",
                "medical-imaging:GetImageSetMetadata",
                "medical-imaging:ListImageSetVersions",
                "medical-imaging:UpdateImageSetMetadata",
                "medical-imaging:DeleteImageSet",
                "medical-imaging:CopyImageSet",
                "medical-imaging:GetImageFrame",
                "medical-imaging:StartDICOMImportJob",
                "medical-imaging:GetDICOMImportJob",
                "medical-imaging:ListDICOMImportJobs",
                "medical-imaging:StartDICOMExportJob",
                "medical-imaging:GetDICOMExportJob",
                "medical-imaging:ListDICOMExportJobs",
                "medical-imaging:ListTagsForResource",
                "medical-imaging:TagResource",
                "medical-imaging:UntagResource"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::your-import-bucket/*",
                "arn:aws:s3:::your-export-bucket/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "kms:Decrypt",
                "kms:GenerateDataKey"
            ],
            "Resource": "arn:aws:kms:*:*:key/*"
        }
    ]
}
```

## Error Handling

The server provides comprehensive error handling:

- **Validation Errors**: Input validation with detailed error messages
- **AWS Service Errors**: Proper handling of AWS API errors
- **Resource Not Found**: Clear messages for missing resources
- **Permission Errors**: Helpful guidance for access issues
- **Rate Limiting**: Automatic retry with exponential backoff

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Verify AWS credentials are configured
   - Check IAM permissions
   - Ensure correct AWS region

2. **Resource Not Found**
   - Verify datastore/image set IDs
   - Check resource exists in specified region
   - Confirm access permissions

3. **Import Job Failures**
   - Check S3 bucket permissions
   - Verify DICOM file format
   - Review import job logs

### Debug Mode

Enable debug logging:

```bash
export FASTMCP_LOG_LEVEL=DEBUG
uvx awslabs.healthimaging-mcp-server@latest
```

## Development

### Local Development Setup

1. Clone the repository:
```bash
git clone https://github.com/awslabs/mcp-server-collection.git
cd mcp-server-collection/src/healthimaging-mcp-server
```

2. Install dependencies:
```bash
uv sync --dev
```

3. Run tests:
```bash
uv run python -m pytest tests/ -v
```

4. Run the server locally:
```bash
uv run python -m awslabs.healthimaging_mcp_server
```

### Testing

The server includes comprehensive tests with 91% coverage:

```bash
# Run all tests
uv run python -m pytest tests/ -v

# Run with coverage
uv run python -m pytest tests/ -v --cov=awslabs.healthimaging_mcp_server --cov-report=html
```

## Contributing

We welcome contributions! Please see our [Contributing Guide](https://github.com/awslabs/mcp-server-collection/blob/main/CONTRIBUTING.md) for details.

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](https://github.com/awslabs/mcp-server-collection/blob/main/LICENSE) file for details.

## Support

For support, please:
1. Check the [troubleshooting section](#troubleshooting)
2. Review [AWS HealthImaging documentation](https://docs.aws.amazon.com/healthimaging/)
3. Open an issue in the [GitHub repository](https://github.com/awslabs/mcp-server-collection/issues)
