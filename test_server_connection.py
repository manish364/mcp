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

"""Simple test script to verify the HealthImaging MCP server is working."""

import asyncio
import json
import sys
from mcp import StdioServerParameters, stdio_client


async def test_server():
    """Test the HealthImaging MCP server connection."""
    print('🔍 Testing HealthImaging MCP Server Connection...')

    # Server command
    server_params = StdioServerParameters(
        command='uv',
        args=['run', 'python', '-m', 'awslabs.healthimaging_mcp_server.server'],
        cwd='src/healthimaging-mcp-server',
    )

    try:
        async with stdio_client(server_params) as (read, write):
            print('✅ Successfully connected to server!')

            # List available tools
            print('\n📋 Available Tools:')
            tools = await read.list_tools()

            for i, tool in enumerate(tools.tools, 1):
                print(f'{i:2d}. {tool.name}')
                if hasattr(tool, 'description') and tool.description:
                    print(f'    {tool.description}')

            print(f'\n🎉 Server is working! Found {len(tools.tools)} tools available.')

            # Test a simple tool (list_datastores)
            print('\n🧪 Testing list_datastores tool...')
            try:
                result = await read.call_tool('list_datastores', {})
                print('✅ list_datastores tool executed successfully!')
                print(f'📊 Result: {json.dumps(result.content, indent=2)[:200]}...')
            except Exception as e:
                print(f'⚠️  Tool execution failed (this is expected without AWS credentials): {e}')

    except Exception as e:
        print(f'❌ Failed to connect to server: {e}')
        return False

    return True


if __name__ == '__main__':
    success = asyncio.run(test_server())
    sys.exit(0 if success else 1)
