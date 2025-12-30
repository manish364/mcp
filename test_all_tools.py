#!/usr/bin/env python3
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

import sys


sys.path.insert(0, 'src/healthimaging-mcp-server')

import asyncio
from awslabs.healthimaging_mcp_server.server import app


async def test_tools():
    """Test multiple MCP tools."""
    # Test 1: list_datastores
    print('Testing list_datastores...')
    try:
        await app.call_tool('list_datastores', {'request': {}})
        print('✓ list_datastores: SUCCESS')
    except Exception as e:
        print(f'✗ list_datastores: ERROR - {e}')

    # Test 2: get_datastore (using first datastore from list)
    print('\nTesting get_datastore...')
    try:
        await app.call_tool(
            'get_datastore', {'request': {'datastore_id': 'ff065a6b17494ed3b3f33da4dfc60a7a'}}
        )
        print('✓ get_datastore: SUCCESS')
    except Exception as e:
        print(f'✗ get_datastore: ERROR - {e}')

    # Test 3: search_image_sets
    print('\nTesting search_image_sets...')
    try:
        await app.call_tool(
            'search_image_sets', {'request': {'datastore_id': 'ff065a6b17494ed3b3f33da4dfc60a7a'}}
        )
        print('✓ search_image_sets: SUCCESS')
    except Exception as e:
        print(f'✗ search_image_sets: ERROR - {e}')

    # Test 4: list_dicom_import_jobs
    print('\nTesting list_dicom_import_jobs...')
    try:
        await app.call_tool(
            'list_dicom_import_jobs',
            {'request': {'datastore_id': 'ff065a6b17494ed3b3f33da4dfc60a7a'}},
        )
        print('✓ list_dicom_import_jobs: SUCCESS')
    except Exception as e:
        print(f'✗ list_dicom_import_jobs: ERROR - {e}')


if __name__ == '__main__':
    asyncio.run(test_tools())
