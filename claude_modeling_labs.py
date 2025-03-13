"""
CML MCP Toolkit - Unified Cisco Modeling Labs API Client

A comprehensive toolkit for interacting with Cisco Modeling Labs (CML) through the
Model Context Protocol (MCP) interface. This toolkit provides a complete set of
functions for lab management, node creation, link management, and configuration.

Authors: Claude AI Assistant
Version: 1.0.0
License: MIT
"""

import os
import sys
import httpx
import json
import warnings
import asyncio
import traceback
from typing import Dict, List, Optional, Any, Union, Tuple
from fastmcp import FastMCP, Context, Image

# Create the MCP server
mcp = FastMCP(
    "CML Lab Builder",
    dependencies=["httpx>=0.26.0", "urllib3>=2.0.0"],
)

# Global state for CML client
cml_auth = None


class CMLAuth:
    """Authentication and request handling for Cisco Modeling Labs"""
    
    def __init__(self, base_url: str, username: str, password: str, verify_ssl: bool = True):
        """
        Initialize the CML authentication client
        
        Args:
            base_url: Base URL of the CML server
            username: Username for CML authentication
            password: Password for CML authentication
            verify_ssl: Whether to verify SSL certificates
        """
        self.base_url = base_url
        self.username = username
        self.password = password
        self.token = None
        self.verify_ssl = verify_ssl
        self.client = httpx.AsyncClient(base_url=base_url, verify=verify_ssl)
        
        # Suppress SSL warnings if verify_ssl is False
        if not verify_ssl:
            try:
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            except ImportError:
                print("urllib3 not available, SSL warning suppression disabled", file=sys.stderr)
    
    async def authenticate(self) -> str:
        """
        Authenticate with CML and get a token
        
        Returns:
            Authentication token
        
        Raises:
            httpx.HTTPStatusError: If authentication fails
        """
        print(f"Authenticating with CML at {self.base_url}", file=sys.stderr)
        response = await self.client.post(
            "/api/v0/authenticate",
            json={"username": self.username, "password": self.password}
        )
        response.raise_for_status()
        self.token = response.text.strip('"')  # Remove any quotes from the token
        self.client.headers.update({"Authorization": f"Bearer {self.token}"})
        
        # Verify the token works
        try:
            auth_check = await self.client.get("/api/v0/authok")
            auth_check.raise_for_status()
            print(f"Authentication successful, token verified", file=sys.stderr)
        except Exception as e:
            print(f"Warning: Token verification failed: {str(e)}", file=sys.stderr)
            
        return self.token
    
    async def request(self, method: str, endpoint: str, **kwargs) -> httpx.Response:
        """
        Make an authenticated request to CML API
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint to call
            **kwargs: Additional arguments to pass to httpx
        
        Returns:
            HTTP response
            
        Raises:
            httpx.HTTPStatusError: If the request fails
        """
        if not self.token:
            await self.authenticate()
        
        # Print debug info to help troubleshoot
        print(f"Making {method} request to {endpoint}", file=sys.stderr)
        
        # Ensure headers contain the token
        if "headers" not in kwargs:
            kwargs["headers"] = {}
        
        # Ensure the Authorization header is set with the current token
        kwargs["headers"]["Authorization"] = f"Bearer {self.token}"
        
        # Make the request
        try:
            response = await self.client.request(method, endpoint, **kwargs)
            
            # If unauthorized, try to re-authenticate once
            if response.status_code == 401:
                print(f"Got 401 response, re-authenticating...", file=sys.stderr)
                await self.authenticate()
                kwargs["headers"]["Authorization"] = f"Bearer {self.token}"
                response = await self.client.request(method, endpoint, **kwargs)
            
            response.raise_for_status()
            return response
        except Exception as e:
            print(f"Request error: {str(e)}", file=sys.stderr)
            raise


# Authentication Tools

@mcp.tool()
async def initialize_client(base_url: str, username: str, password: str, verify_ssl: bool = True) -> str:
    """
    Initialize the CML client with authentication credentials
    
    Args:
        base_url: Base URL of the CML server (e.g., https://cml-server)
        username: Username for CML authentication
        password: Password for CML authentication
        verify_ssl: Whether to verify SSL certificates (set to False for self-signed certificates)
    
    Returns:
        A success message if authentication is successful
    """
    global cml_auth
    
    # Fix URL if it doesn't have a scheme
    if not base_url.startswith(('http://', 'https://')):
        base_url = f"https://{base_url}"
    
    print(f"Initializing CML client with base_url: {base_url}", file=sys.stderr)
    cml_auth = CMLAuth(base_url, username, password, verify_ssl)
    
    try:
        token = await cml_auth.authenticate()
        print(f"Token received: {token[:10]}...", file=sys.stderr)  # Only print first 10 chars for security
        ssl_status = "enabled" if verify_ssl else "disabled (accepting self-signed certificates)"
        return f"Successfully authenticated with CML at {base_url} (SSL verification: {ssl_status})"
    except httpx.HTTPStatusError as e:
        return f"Authentication failed: {str(e)}"
    except Exception as e:
        print(f"Error connecting to CML: {str(e)}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return f"Error connecting to CML: {str(e)}"


# Helper Functions

def _check_auth() -> Union[None, Dict[str, str]]:
    """
    Check if the client is authenticated
    
    Returns:
        None if authenticated, error dictionary if not
    """
    if not cml_auth:
        return {"error": "You must initialize the client first with initialize_client()"}
    return None


def _handle_api_error(operation: str, error: Exception) -> Dict[str, Any]:
    """
    Handle API errors consistently
    
    Args:
        operation: Description of the operation that failed
        error: Exception that was raised
    
    Returns:
        Error dictionary with consistent format
    """
    print(f"Error during {operation}: {str(error)}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    return {"error": f"Error during {operation}: {str(error)}"}


# Lab Management Tools

@mcp.tool()
async def list_labs() -> str:
    """
    List all labs in CML
    
    Returns:
        A formatted list of all available labs
    """
    auth_check = _check_auth()
    if auth_check:
        return auth_check["error"]
    
    try:
        print("Attempting to list labs...", file=sys.stderr)
        response = await cml_auth.request("GET", "/api/v0/labs")
        labs = response.json()
        
        print(f"Found {len(labs)} labs", file=sys.stderr)
        
        if not labs:
            return "No labs found in CML."
        
        # Format the response nicely
        result = "Available Labs:\n\n"
        for lab_id, lab_info in labs.items():
            result += f"- {lab_info.get('title', 'Untitled')} (ID: {lab_id})\n"
            if lab_info.get('description'):
                result += f"  Description: {lab_info['description']}\n"
            result += f"  State: {lab_info.get('state', 'unknown')}\n"
        
        return result
    except Exception as e:
        return f"Error listing labs: {str(e)}"


@mcp.tool()
async def create_lab(title: str, description: str = "") -> Dict[str, str]:
    """
    Create a new lab in CML
    
    Args:
        title: Title of the new lab
        description: Optional description for the lab
    
    Returns:
        Dictionary containing lab ID and confirmation message
    """
    auth_check = _check_auth()
    if auth_check:
        return auth_check
    
    try:
        print(f"Creating lab with title: {title}", file=sys.stderr)
        
        response = await cml_auth.request(
            "POST", 
            "/api/v0/labs",
            json={"title": title, "description": description}
        )
        
        lab_data = response.json()
        print(f"Lab creation response: {lab_data}", file=sys.stderr)
        
        lab_id = lab_data.get("id")
        
        if not lab_id:
            return {"error": "Failed to create lab, no lab ID returned"}
        
        return {
            "lab_id": lab_id,
            "message": f"Created lab '{title}' with ID: {lab_id}",
            "status": "success"
        }
    except Exception as e:
        return _handle_api_error("create_lab", e)


@mcp.tool()
async def get_lab_details(lab_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific lab
    
    Args:
        lab_id: ID of the lab to get details for
    
    Returns:
        Dictionary containing lab details
    """
    auth_check = _check_auth()
    if auth_check:
        return auth_check
    
    try:
        response = await cml_auth.request("GET", f"/api/v0/labs/{lab_id}")
        lab_details = response.json()
        return lab_details
    except Exception as e:
        return _handle_api_error("get_lab_details", e)


@mcp.tool()
async def delete_lab(lab_id: str) -> str:
    """
    Delete a lab from CML
    
    Args:
        lab_id: ID of the lab to delete
    
    Returns:
        Confirmation message
    """
    auth_check = _check_auth()
    if auth_check:
        return auth_check["error"]
    
    try:
        # First check if the lab is running
        lab_details = await get_lab_details(lab_id)
        if isinstance(lab_details, dict) and lab_details.get("state") == "STARTED":
            # Stop the lab first
            await stop_lab(lab_id)
            # Wait for the lab to fully stop
            await asyncio.sleep(2)
        
        response = await cml_auth.request("DELETE", f"/api/v0/labs/{lab_id}")
        return f"Lab {lab_id} deleted successfully"
    except Exception as e:
        return f"Error deleting lab: {str(e)}"


# Node Definition Management Tools

@mcp.tool()
async def list_node_definitions() -> Union[Dict[str, Any], str]:
    """
    List all available node definitions in CML
    
    Returns:
        Dictionary of available node definitions or error message
    """
    auth_check = _check_auth()
    if auth_check:
        return auth_check["error"]
    
    try:
        response = await cml_auth.request("GET", "/api/v0/node_definitions")
        node_defs = response.json()
        
        # If the response is a list, convert it to a dictionary
        if isinstance(node_defs, list):
            print(f"Converting node definitions list to dictionary", file=sys.stderr)
            result = {}
            for node_def in node_defs:
                node_id = node_def.get("id")
                if node_id:
                    result[node_id] = node_def
            return result
        
        # Format the result to be more readable
        result = {}
        for node_id, node_info in node_defs.items():
            result[node_id] = {
                "description": node_info.get("description", ""),
                "type": node_info.get("type", ""),
                "interfaces": node_info.get("interfaces", []),
            }
        
        return result
    except Exception as e:
        return f"Error listing node definitions: {str(e)}"


# Node Management Tools

@mcp.tool()
async def get_lab_nodes(lab_id: str) -> Union[Dict[str, Any], str]:
    """
    Get all nodes in a specific lab
    
    Args:
        lab_id: ID of the lab
    
    Returns:
        Dictionary of nodes in the lab or error message
    """
    auth_check = _check_auth()
    if auth_check:
        return auth_check["error"]
    
    try:
        response = await cml_auth.request("GET", f"/api/v0/labs/{lab_id}/nodes")
        nodes = response.json()
        
        # If the response is a list, convert it to a dictionary
        if isinstance(nodes, list):
            print(f"Converting nodes list to dictionary", file=sys.stderr)
            result = {}
            for node in nodes:
                node_id = node.get("id")
                if node_id:
                    result[node_id] = node
            return result
        
        return nodes
    except Exception as e:
        return f"Error getting lab nodes: {str(e)}"


@mcp.tool()
async def add_node(
    lab_id: str, 
    label: str, 
    node_definition: str, 
    x: int = 0, 
    y: int = 0,
    populate_interfaces: bool = True,
    ram: Optional[int] = None,
    cpu_limit: Optional[int] = None,
    parameters: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Add a node to the specified lab
    
    Args:
        lab_id: ID of the lab
        label: Label for the new node
        node_definition: Type of node (e.g., 'iosv', 'csr1000v')
        x: X coordinate for node placement
        y: Y coordinate for node placement
        populate_interfaces: Whether to automatically create interfaces
        ram: RAM allocation for the node (optional)
        cpu_limit: CPU limit for the node (optional)
        parameters: Node-specific parameters (optional)
    
    Returns:
        Dictionary with node ID and confirmation message
    """
    auth_check = _check_auth()
    if auth_check:
        return auth_check
    
    try:
        # Construct the node data payload
        node_data = {
            "label": label,
            "node_definition": node_definition,
            "x": x,
            "y": y,
            "parameters": parameters or {},
            "tags": [],
            "hide_links": False
        }
        
        # Add optional parameters if provided
        if ram is not None:
            node_data["ram"] = ram
        
        if cpu_limit is not None:
            node_data["cpu_limit"] = cpu_limit
        
        # Add populate_interfaces as a query parameter if needed
        endpoint = f"/api/v0/labs/{lab_id}/nodes"
        if populate_interfaces:
            endpoint += "?populate_interfaces=true"
        
        # Make the API request with explicit Content-Type header
        headers = {"Content-Type": "application/json"}
        response = await cml_auth.request(
            "POST",
            endpoint,
            json=node_data,
            headers=headers
        )
        
        # Process the response
        result = response.json()
        node_id = result.get("id")
        
        if not node_id:
            return {"error": "Failed to create node, no node ID returned", "response": result}
        
        return {
            "node_id": node_id,
            "message": f"Added node '{label}' with ID: {node_id}",
            "status": "success",
            "details": result
        }
    except Exception as e:
        return _handle_api_error("add_node", e)


@mcp.tool()
async def create_router(
    lab_id: str,
    label: str,
    x: int = 0,
    y: int = 0
) -> Dict[str, Any]:
    """
    Create a router with the 'iosv' node definition
    
    Args:
        lab_id: ID of the lab
        label: Label for the new router
        x: X coordinate for node placement
        y: Y coordinate for node placement
    
    Returns:
        Dictionary with node ID and confirmation message
    """
    auth_check = _check_auth()
    if auth_check:
        return auth_check
    
    # Use add_node with the router node definition
    return await add_node(lab_id, label, "iosv", x, y, True)


@mcp.tool()
async def create_switch(
    lab_id: str,
    label: str,
    num_interfaces: int = 8,
    x: int = 0,
    y: int = 0
) -> Dict[str, Any]:
    """
    Create a switch with a specified number of interfaces
    
    Args:
        lab_id: ID of the lab
        label: Label for the new switch
        num_interfaces: Number of interfaces to create (default: 8)
        x: X coordinate for node placement
        y: Y coordinate for node placement
    
    Returns:
        Dictionary with node ID and confirmation message
    """
    auth_check = _check_auth()
    if auth_check:
        return auth_check
    
    try:
        # Use add_node with the switch node definition and parameters for interfaces
        return await add_node(
            lab_id,
            label,
            "iosvl2",
            x,
            y,
            True,
            ram=None,
            cpu_limit=None,
            parameters={"slot1": str(num_interfaces)}  # Configure the number of interfaces
        )
    except Exception as e:
        return _handle_api_error("create_switch", e)


# Interface Management Tools

@mcp.tool()
async def get_node_interfaces(lab_id: str, node_id: str) -> Union[Dict[str, Any], str, List[str]]:
    """
    Get interfaces for a specific node
    
    Args:
        lab_id: ID of the lab
        node_id: ID of the node
    
    Returns:
        Dictionary of node interfaces or error message or list of interface IDs
    """
    auth_check = _check_auth()
    if auth_check:
        return auth_check["error"]
    
    try:
        response = await cml_auth.request("GET", f"/api/v0/labs/{lab_id}/nodes/{node_id}/interfaces")
        interfaces = response.json()
        
        # Check if the response is a list of interface IDs
        if isinstance(interfaces, list):
            print(f"Got list of interface IDs: {interfaces}", file=sys.stderr)
            return interfaces
        elif isinstance(interfaces, str):
            # If it's a string, it might be a concatenated list of UUIDs
            print(f"Got string of interface IDs: {interfaces}", file=sys.stderr)
            # Parse as UUIDs (36 characters per UUID)
            if len(interfaces) % 36 == 0:
                return [interfaces[i:i+36] for i in range(0, len(interfaces), 36)]
            else:
                return interfaces
        else:
            # If it's a dictionary, return it as is
            return interfaces
    except Exception as e:
        print(f"Error getting node interfaces: {str(e)}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return f"Error getting node interfaces: {str(e)}"


@mcp.tool()
async def get_physical_interfaces(lab_id: str, node_id: str) -> Union[Dict[str, Any], List[Dict[str, Any]], str]:
    """
    Get all physical interfaces for a specific node
    
    Args:
        lab_id: ID of the lab
        node_id: ID of the node
    
    Returns:
        List of physical interfaces or error message
    """
    auth_check = _check_auth()
    if auth_check:
        return auth_check["error"]
    
    try:
        # First get all interfaces
        interfaces_response = await get_node_interfaces(lab_id, node_id)
        
        # Handle different return types
        interface_ids = []
        if isinstance(interfaces_response, str) and "Error" in interfaces_response:
            return interfaces_response
        elif isinstance(interfaces_response, list):
            interface_ids = interfaces_response
        elif isinstance(interfaces_response, str):
            # Parse as UUIDs if needed
            if len(interfaces_response) % 36 == 0:
                interface_ids = [interfaces_response[i:i+36] for i in range(0, len(interfaces_response), 36)]
            else:
                return f"Unexpected interface response format: {interfaces_response}"
        elif isinstance(interfaces_response, dict):
            interface_ids = list(interfaces_response.keys())
        else:
            return f"Unexpected interface response type: {type(interfaces_response)}"
        
        # Get details for each interface and filter for physical interfaces
        physical_interfaces = []
        for interface_id in interface_ids:
            interface_details = await cml_auth.request("GET", f"/api/v0/labs/{lab_id}/interfaces/{interface_id}")
            interface_data = interface_details.json()
            
            # Check if it's a physical interface
            is_physical = interface_data.get("type") == "physical"
            
            # If type is not present, check other attributes that might indicate a physical interface
            if "type" not in interface_data:
                # Most physical interfaces have a slot number
                if "slot" in interface_data:
                    is_physical = True
            
            if is_physical:
                physical_interfaces.append(interface_data)
        
        if not physical_interfaces:
            return f"No physical interfaces found for node {node_id}"
        
        return physical_interfaces
    except Exception as e:
        return _handle_api_error("get_physical_interfaces", e)


@mcp.tool()
async def create_interface(lab_id: str, node_id: str, slot: int = 4) -> Dict[str, Any]:
    """
    Create an interface on a node
    
    Args:
        lab_id: ID of the lab
        node_id: ID of the node
        slot: Slot number for the interface (default: 4)
    
    Returns:
        Dictionary with interface ID and confirmation message
    """
    auth_check = _check_auth()
    if auth_check:
        return auth_check
    
    try:
        # Check if the lab is running
        lab_details = await get_lab_details(lab_id)
        if isinstance(lab_details, dict) and lab_details.get("state") == "STARTED":
            return {"error": "Cannot create interfaces while the lab is running. Please stop the lab first."}
        
        print(f"Creating interface on node {node_id}, slot {slot}", file=sys.stderr)
        
        # Construct the proper payload format
        interface_data = {
            "node": node_id,
            "slot": slot
        }
        
        print(f"Interface creation payload: {interface_data}", file=sys.stderr)
        
        # Make the API request
        response = await cml_auth.request(
            "POST", 
            f"/api/v0/labs/{lab_id}/interfaces",
            json=interface_data
        )
        
        # Process the response
        result = response.json()
        print(f"Interface creation response: {result}", file=sys.stderr)
        
        # Handle different response formats
        if isinstance(result, list) and len(result) > 0:
            # Sometimes the API returns a list of created interfaces
            interface_id = result[0].get("id")
            interface_label = result[0].get("label")
            return {
                "interface_id": interface_id,
                "message": f"Created interface {interface_label} on node {node_id}, slot {slot}",
                "status": "success",
                "details": result
            }
        elif isinstance(result, dict):
            # Sometimes it returns a single object
            interface_id = result.get("id")
            interface_label = result.get("label")
            if interface_id:
                return {
                    "interface_id": interface_id,
                    "message": f"Created interface {interface_label} on node {node_id}, slot {slot}",
                    "status": "success",
                    "details": result
                }
        
        return {"error": "Failed to create interface, unexpected response format", "response": result}
    except Exception as e:
        return _handle_api_error("create_interface", e)


# Link Management Tools

async def find_available_interface(lab_id: str, node_id: str) -> Union[str, Dict[str, str]]:
    """
    Find an available physical interface on a node
    
    Args:
        lab_id: ID of the lab
        node_id: ID of the node
        
    Returns:
        Interface ID or error dictionary
    """
    auth_check = _check_auth()
    if auth_check:
        return auth_check
    
    try:
        # Get interfaces for the node with operational=true to get details
        interfaces_response = await cml_auth.request(
            "GET", 
            f"/api/v0/labs/{lab_id}/nodes/{node_id}/interfaces?operational=true"
        )
        interfaces = interfaces_response.json()
        
        # Ensure we have an array of interfaces
        if isinstance(interfaces, str):
            interfaces = interfaces.split()
        elif isinstance(interfaces, dict):
            interfaces = list(interfaces.keys())
        
        # Make sure we have interfaces to work with
        if not interfaces:
            return {"error": f"No interfaces found for node {node_id}"}
        
        # Find first available physical interface
        for interface_id in interfaces:
            # Get detailed info for this interface
            interface_detail = await cml_auth.request(
                "GET", 
                f"/api/v0/labs/{lab_id}/interfaces/{interface_id}?operational=true"
            )
            interface_data = interface_detail.json()
            
            # Check if physical and not connected
            if (interface_data.get("type") == "physical" and 
                interface_data.get("is_connected") == False):
                return interface_id
        
        return {"error": f"No available physical interface found for node {node_id}"}
    except Exception as e:
        return _handle_api_error("find_available_interface", e)


@mcp.tool()
async def create_link_v3(lab_id: str, interface_id_a: str, interface_id_b: str) -> Dict[str, Any]:
    """
    Create a link between two interfaces in a lab
    
    Args:
        lab_id: ID of the lab
        interface_id_a: ID of the first interface
        interface_id_b: ID of the second interface
    
    Returns:
        Dictionary with link ID and confirmation message
    """
    auth_check = _check_auth()
    if auth_check:
        return auth_check
    
    try:
        print(f"Creating link between interfaces {interface_id_a} and {interface_id_b}", file=sys.stderr)
        
        # Try the standard format with src_int and dst_int
        link_data = {
            "src_int": interface_id_a,
            "dst_int": interface_id_b
        }
        
        headers = {"Content-Type": "application/json"}
        response = await cml_auth.request(
            "POST", 
            f"/api/v0/labs/{lab_id}/links",
            json=link_data,
            headers=headers
        )
        
        result = response.json()
        print(f"Link creation response: {result}", file=sys.stderr)
        
        # Extract the link ID from the response
        link_id = result.get("id")
        if not link_id:
            return {"error": "Failed to create link, no link ID returned", "response": result}
        
        return {
            "link_id": link_id,
            "message": f"Created link between interfaces {interface_id_a} and {interface_id_b}",
            "status": "success",
            "details": result
        }
    except Exception as e:
        # If the first format failed, try an alternative format
        try:
            print("First format failed, trying alternative format...", file=sys.stderr)
            link_data_alt = {
                "i1": interface_id_a,
                "i2": interface_id_b
            }
            
            response_alt = await cml_auth.request(
                "POST", 
                f"/api/v0/labs/{lab_id}/links",
                json=link_data_alt,
                headers=headers
            )
            
            result_alt = response_alt.json()
            print(f"Link creation response (alt format): {result_alt}", file=sys.stderr)
            
            link_id_alt = result_alt.get("id")
            if link_id_alt:
                return {
                    "link_id": link_id_alt,
                    "message": f"Created link between interfaces {interface_id_a} and {interface_id_b} using alternative format",
                    "status": "success",
                    "details": result_alt
                }
            
            return {"error": "Failed to create link with both formats"}
        except Exception as alt_err:
            print(f"Alternative format also failed: {str(alt_err)}", file=sys.stderr)
            return _handle_api_error("create_link", e)
    

@mcp.tool()
async def link_nodes(lab_id: str, node_id_a: str, node_id_b: str) -> Dict[str, Any]:
    """
    Create a link between two nodes by automatically selecting appropriate interfaces
    
    Args:
        lab_id: ID of the lab
        node_id_a: ID of the first node
        node_id_b: ID of the second node
    
    Returns:
        Dictionary with link ID and confirmation message
    """
    auth_check = _check_auth()
    if auth_check:
        return auth_check
    
    try:
        # Find available interfaces on both nodes
        interface_a = await find_available_interface(lab_id, node_id_a)
        if isinstance(interface_a, dict) and "error" in interface_a:
            return interface_a
        
        interface_b = await find_available_interface(lab_id, node_id_b)
        if isinstance(interface_b, dict) and "error" in interface_b:
            return interface_b
        
        # Create the link using these interfaces
        return await create_link_v3(lab_id, interface_a, interface_b)
    except Exception as e:
        return _handle_api_error("link_nodes", e)


@mcp.tool()
async def get_lab_links(lab_id: str) -> Union[Dict[str, Any], str]:
    """
    Get all links in a specific lab
    
    Args:
        lab_id: ID of the lab
    
    Returns:
        Dictionary of links in the lab or error message
    """
    auth_check = _check_auth()
    if auth_check:
        return auth_check["error"]
    
    try:
        response = await cml_auth.request("GET", f"/api/v0/labs/{lab_id}/links")
        links = response.json()
        
        # If the response is a list, convert it to a dictionary
        if isinstance(links, list):
            print(f"Converting links list to dictionary", file=sys.stderr)
            result = {}
            for link in links:
                link_id = link.get("id")
                if link_id:
                    result[link_id] = link
            return result
        
        return links
    except Exception as e:
        return f"Error getting lab links: {str(e)}"


@mcp.tool()
async def delete_link(lab_id: str, link_id: str) -> str:
    """
    Delete a link from a lab
    
    Args:
        lab_id: ID of the lab
        link_id: ID of the link to delete
    
    Returns:
        Confirmation message
    """
    auth_check = _check_auth()
    if auth_check:
        return auth_check["error"]
    
    try:
        response = await cml_auth.request("DELETE", f"/api/v0/labs/{lab_id}/links/{link_id}")
        return f"Link {link_id} deleted successfully"
    except Exception as e:
        return f"Error deleting link: {str(e)}"


# Configuration Management Tools

@mcp.tool()
async def configure_node(lab_id: str, node_id: str, config: str) -> str:
    """
    Configure a node with the specified configuration
    
    Args:
        lab_id: ID of the lab
        node_id: ID of the node to configure
        config: Configuration text to apply
    
    Returns:
        Confirmation message
    """
    auth_check = _check_auth()
    if auth_check:
        return auth_check["error"]
    
    try:
        response = await cml_auth.request(
            "PUT",
            f"/api/v0/labs/{lab_id}/nodes/{node_id}/config",
            content=config
        )
        
        return f"Configuration applied to node {node_id}"
    except Exception as e:
        return f"Error configuring node: {str(e)}"


@mcp.tool()
async def get_node_config(lab_id: str, node_id: str) -> str:
    """
    Get the current configuration of a node
    
    Args:
        lab_id: ID of the lab
        node_id: ID of the node
    
    Returns:
        Node configuration text or error message
    """
    auth_check = _check_auth()
    if auth_check:
        return auth_check["error"]
    
    try:
        response = await cml_auth.request("GET", f"/api/v0/labs/{lab_id}/nodes/{node_id}/config")
        config = response.text
        return config
    except Exception as e:
        return f"Error getting node configuration: {str(e)}"


# Lab Control Tools

@mcp.tool()
async def start_lab(lab_id: str) -> str:
    """
    Start the specified lab
    
    Args:
        lab_id: ID of the lab to start
    
    Returns:
        Confirmation message
    """
    auth_check = _check_auth()
    if auth_check:
        return auth_check["error"]
    
    try:
        response = await cml_auth.request("PUT", f"/api/v0/labs/{lab_id}/start")
        return f"Lab {lab_id} started successfully"
    except Exception as e:
        return f"Error starting lab: {str(e)}"


@mcp.tool()
async def wait_for_lab_nodes(lab_id: str, timeout: int = 60) -> str:
    """
    Wait for all nodes in a lab to reach the STARTED state
    
    Args:
        lab_id: ID of the lab
        timeout: Maximum time to wait in seconds (default: 60)
    
    Returns:
        Status message
    """
    auth_check = _check_auth()
    if auth_check:
        return auth_check["error"]
    
    try:
        # Check if the lab is running
        lab_details = await get_lab_details(lab_id)
        if not isinstance(lab_details, dict) or lab_details.get("state") != "STARTED":
            return "Lab is not in STARTED state. Start the lab first."
        
        print(f"Waiting for nodes in lab {lab_id} to initialize...", file=sys.stderr)
        
        # Get nodes
        nodes = await get_lab_nodes(lab_id)
        if isinstance(nodes, str) and "Error" in nodes:
            return nodes
        
        start_time = asyncio.get_event_loop().time()
        all_ready = False
        
        while not all_ready and (asyncio.get_event_loop().time() - start_time) < timeout:
            all_ready = True
            
            for node_id, node in nodes.items():
                node_info = await cml_auth.request("GET", f"/api/v0/labs/{lab_id}/nodes/{node_id}")
                node_data = node_info.json()
                
                state = node_data.get("state", "UNKNOWN")
                print(f"Node {node_data.get('label', 'unknown')} state: {state}", file=sys.stderr)
                
                if state != "STARTED":
                    all_ready = False
            
            if not all_ready:
                await asyncio.sleep(5)  # Wait 5 seconds before checking again
        
        if all_ready:
            return "All nodes in the lab are initialized and ready"
        else:
            return f"Timeout reached ({timeout} seconds). Some nodes may not be fully initialized."
    except Exception as e:
        print(f"Error waiting for nodes: {str(e)}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return f"Error waiting for nodes: {str(e)}"


@mcp.tool()
async def stop_lab(lab_id: str) -> str:
    """
    Stop the specified lab
    
    Args:
        lab_id: ID of the lab to stop
    
    Returns:
        Confirmation message
    """
    auth_check = _check_auth()
    if auth_check:
        return auth_check["error"]
    
    try:
        response = await cml_auth.request("PUT", f"/api/v0/labs/{lab_id}/stop")
        return f"Lab {lab_id} stopped successfully"
    except Exception as e:
        return f"Error stopping lab: {str(e)}"


@mcp.tool()
async def get_lab_topology(lab_id: str) -> str:
    """
    Get a detailed summary of the lab topology
    
    Args:
        lab_id: ID of the lab
    
    Returns:
        Formatted summary of the lab topology
    """
    auth_check = _check_auth()
    if auth_check:
        return auth_check["error"]
    
    try:
        # Get lab details
        lab_details = await get_lab_details(lab_id)
        if isinstance(lab_details, dict) and "error" in lab_details:
            return lab_details["error"]
        
        # Get nodes
        nodes = await get_lab_nodes(lab_id)
        if isinstance(nodes, str) and "Error" in nodes:
            return nodes
        
        # Get links
        links = await get_lab_links(lab_id)
        if isinstance(links, str) and "Error" in links:
            return links
        
        # Create a topology summary
        result = f"Lab Topology: {lab_details.get('title', 'Untitled')}\n"
        result += f"State: {lab_details.get('state', 'unknown')}\n"
        result += f"Description: {lab_details.get('description', 'None')}\n\n"
        
        # Add nodes
        result += "Nodes:\n"
        for node_id, node in nodes.items():
            result += f"- {node.get('label', 'Unnamed')} (ID: {node_id})\n"
            result += f"  Type: {node.get('node_definition', 'unknown')}\n"
            result += f"  State: {node.get('state', 'unknown')}\n"
        
        # Add links
        result += "\nLinks:\n"
        for link_id, link in links.items():
            src_node_id = link.get('src_node')
            dst_node_id = link.get('dst_node')
            
            if src_node_id in nodes and dst_node_id in nodes:
                src_node = nodes[src_node_id].get('label', src_node_id)
                dst_node = nodes[dst_node_id].get('label', dst_node_id)
                result += (f"- Link {link_id}: {src_node} ({link.get('src_int', 'unknown')}) → "
                           f"{dst_node} ({link.get('dst_int', 'unknown')})\n")
            else:
                result += f"- Link {link_id}: {src_node_id}:{link.get('src_int')} → {dst_node_id}:{link.get('dst_int')}\n"
        
        return result
    except Exception as e:
        return f"Error getting lab topology: {str(e)}"


# Pre-built Lab Templates

@mcp.tool()
async def create_simple_network(
    title: str = "Simple Network",
    description: str = "A simple network with a router and switch"
) -> Dict[str, Any]:
    """
    Create a simple network lab with a router and switch
    
    Args:
        title: Title for the new lab
        description: Optional description for the lab
    
    Returns:
        Dictionary with lab details
    """
    auth_check = _check_auth()
    if auth_check:
        return auth_check
    
    try:
        # Create the lab
        lab_response = await create_lab(title, description)
        if "error" in lab_response:
            return lab_response
        
        lab_id = lab_response["lab_id"]
        
        # Create router and switch
        router_result = await create_router(lab_id, "Router1", 50, 50)
        if "error" in router_result:
            return {"error": f"Failed to create router: {router_result['error']}"}
        
        switch_result = await create_switch(lab_id, "Switch1", 8, 50, 150)
        if "error" in switch_result:
            return {"error": f"Failed to create switch: {switch_result['error']}"}
        
        # Connect the devices
        link_result = await link_nodes(lab_id, router_result["node_id"], switch_result["node_id"])
        
        return {
            "lab_id": lab_id,
            "title": title,
            "router_id": router_result["node_id"],
            "switch_id": switch_result["node_id"],
            "link_status": "success" if "link_id" in link_result else "failed",
            "link_details": link_result
        }
    except Exception as e:
        return _handle_api_error("create_simple_network", e)


@mcp.tool()
async def generate_switch_stp_config(
    switch_name: str,
    stp_mode: str = "mst",  # Options: "mst", "rapid-pvst", "pvst"
    role: str = "root",  # Options: "root", "secondary", "normal"
    vlans: List[int] = [1, 10, 20, 30, 40],
    mst_instance_mapping: Optional[Dict[int, List[int]]] = None
) -> str:
    """
    Generate Spanning Tree Protocol configuration for a switch
    
    Args:
        switch_name: Name of the switch
        stp_mode: STP mode to configure ("mst", "rapid-pvst", or "pvst")
        role: Role of the switch ("root", "secondary", or "normal")
        vlans: List of VLANs to configure
        mst_instance_mapping: For MST mode, mapping of MST instances to VLANs
        
    Returns:
        Configuration text for the switch
    """
    
    config_lines = [
        f"! {switch_name} Configuration",
        "!",
        f"hostname {switch_name}",
        "!",
        "! VLANs Configuration"
    ]
    
    # Create VLANs
    for vlan_id in vlans:
        if vlan_id == 1:
            continue  # Skip default VLAN 1
        config_lines.extend([
            f"vlan {vlan_id}",
            f" name VLAN{vlan_id}",
            "!"
        ])
    
    # STP Mode Configuration
    config_lines.append("! Spanning-tree Configuration")
    
    if stp_mode == "mst":
        config_lines.append("spanning-tree mode mst")
        
        # Configure MST region and instances
        config_lines.extend([
            "!",
            "! Configure MST instance to VLAN mapping",
            "spanning-tree mst configuration",
            f" name {switch_name}-REGION",
            " revision 1"
        ])
        
        # Add instance to VLAN mappings
        if mst_instance_mapping:
            for instance, mapped_vlans in mst_instance_mapping.items():
                vlan_list = ",".join(map(str, mapped_vlans))
                config_lines.append(f" instance {instance} vlan {vlan_list}")
        else:
            # Default mapping if none provided
            config_lines.extend([
                " instance 1 vlan 10, 20",
                " instance 2 vlan 30, 40"
            ])
        
        # Configure priorities based on role
        if role == "root":
            config_lines.extend([
                "!",
                "! Set as MST root for instance 0 (CST)",
                "spanning-tree mst 0 priority 4096",
                "spanning-tree mst 1 priority 4096",
                "spanning-tree mst 2 priority 4096"
            ])
        elif role == "secondary":
            config_lines.extend([
                "!",
                "! Set as MST secondary root",
                "spanning-tree mst 0 priority 8192",
                "spanning-tree mst 1 priority 8192",
                "spanning-tree mst 2 priority 8192"
            ])
        else:
            # Normal role with higher priority
            config_lines.extend([
                "!",
                "! Normal switch (not root)",
                "spanning-tree mst 0 priority 32768",
                "spanning-tree mst 1 priority 32768",
                "spanning-tree mst 2 priority 32768"
            ])
    
    elif stp_mode == "rapid-pvst":
        config_lines.append("spanning-tree mode rapid-pvst")
        
        # Configure priorities per VLAN based on role
        if role == "root":
            for vlan_id in vlans:
                config_lines.append(f"spanning-tree vlan {vlan_id} priority 4096")
        elif role == "secondary":
            for vlan_id in vlans:
                config_lines.append(f"spanning-tree vlan {vlan_id} priority 8192")
        else:
            # Normal role with higher priority for specific VLANs
            for vlan_id in vlans:
                config_lines.append(f"spanning-tree vlan {vlan_id} priority 32768")
    
    else:  # PVST (default)
        config_lines.append("spanning-tree mode pvst")
        
        # Configure priorities per VLAN based on role
        if role == "root":
            for vlan_id in vlans:
                config_lines.append(f"spanning-tree vlan {vlan_id} priority 4096")
        elif role == "secondary":
            for vlan_id in vlans:
                config_lines.append(f"spanning-tree vlan {vlan_id} priority 8192")
        else:
            # Normal role with higher priority
            for vlan_id in vlans:
                config_lines.append(f"spanning-tree vlan {vlan_id} priority 32768")
    
    # Common STP settings regardless of mode
    config_lines.extend([
        "!",
        "! Common STP features",
        "spanning-tree extend system-id",
        "spanning-tree portfast edge default",
        "spanning-tree portfast bpduguard default"
    ])
    
    # Interface configuration
    config_lines.extend([
        "!",
        "! Configure interfaces",
        "!",
        "interface range GigabitEthernet0/0 - 7",
        " switchport trunk encapsulation dot1q",
        " switchport mode trunk",
        " switchport trunk allowed vlan all",
        " no shutdown"
    ])
    
    # Management VLAN interface 
    config_lines.extend([
        "!",
        "! Management interface",
        "interface Vlan1",
        f" ip address 10.0.0.{vlans[0]} 255.255.255.0",
        " no shutdown",
        "!",
        "! End of configuration"
    ])
    
    return "\n".join(config_lines)


@mcp.tool()
async def create_stp_lab(
    title: str = "STP Test Lab",
    description: str = "Spanning Tree Protocol test lab with multiple STP versions",
    num_switches: int = 6,
    interfaces_per_switch: int = 8
) -> Dict[str, Any]:
    """
    Create a comprehensive Spanning Tree Protocol test lab
    
    Args:
        title: Title for the lab
        description: Description for the lab
        num_switches: Number of switches to create (default: 6)
        interfaces_per_switch: Number of interfaces per switch (default: 8)
    
    Returns:
        Dictionary with lab details and node IDs
    """
    auth_check = _check_auth()
    if auth_check:
        return auth_check
    
    try:
        # Create the lab
        lab_response = await create_lab(title, description)
        if "error" in lab_response:
            return lab_response
        
        lab_id = lab_response["lab_id"]
        
        # Create the switches with enhanced interface count
        switches = []
        
        # Core switches (top row)
        sw1_result = await create_switch(
            lab_id, 
            "SW1-Core", 
            interfaces_per_switch, 
            x=100, 
            y=100
        )
        switches.append({"name": "SW1-Core", "id": sw1_result["node_id"], "layer": "core"})
        
        sw2_result = await create_switch(
            lab_id, 
            "SW2-Core", 
            interfaces_per_switch, 
            x=300, 
            y=100
        )
        switches.append({"name": "SW2-Core", "id": sw2_result["node_id"], "layer": "core"})
        
        # Distribution switches (middle row) if we have more than 2 switches
        if num_switches > 2:
            sw3_result = await create_switch(
                lab_id, 
                "SW3-Distribution", 
                interfaces_per_switch, 
                x=50, 
                y=200
            )
            switches.append({"name": "SW3-Distribution", "id": sw3_result["node_id"], "layer": "distribution"})
            
            sw4_result = await create_switch(
                lab_id, 
                "SW4-Distribution", 
                interfaces_per_switch, 
                x=350, 
                y=200
            )
            switches.append({"name": "SW4-Distribution", "id": sw4_result["node_id"], "layer": "distribution"})
        
        # Access switches (bottom row) if we have more than 4 switches
        if num_switches > 4:
            sw5_result = await create_switch(
                lab_id, 
                "SW5-Access", 
                interfaces_per_switch, 
                x=150, 
                y=300
            )
            switches.append({"name": "SW5-Access", "id": sw5_result["node_id"], "layer": "access"})
            
            sw6_result = await create_switch(
                lab_id, 
                "SW6-Access", 
                interfaces_per_switch, 
                x=250, 
                y=300
            )
            switches.append({"name": "SW6-Access", "id": sw6_result["node_id"], "layer": "access"})
        
        # Create links between switches to form a redundant topology
        links = []
        
        # Connect core switches
        if len(switches) >= 2:
            link1 = await link_nodes(lab_id, switches[0]["id"], switches[1]["id"])
            links.append({"from": switches[0]["name"], "to": switches[1]["name"], "id": link1.get("link_id")})
        
        # Connect distribution to core (if we have distribution switches)
        if len(switches) >= 4:
            # Connect SW1-Core to both distribution switches
            link2 = await link_nodes(lab_id, switches[0]["id"], switches[2]["id"])
            links.append({"from": switches[0]["name"], "to": switches[2]["name"], "id": link2.get("link_id")})
            
            link3 = await link_nodes(lab_id, switches[0]["id"], switches[3]["id"])
            links.append({"from": switches[0]["name"], "to": switches[3]["name"], "id": link3.get("link_id")})
            
            # Connect SW2-Core to both distribution switches
            link4 = await link_nodes(lab_id, switches[1]["id"], switches[2]["id"])
            links.append({"from": switches[1]["name"], "to": switches[2]["name"], "id": link4.get("link_id")})
            
            link5 = await link_nodes(lab_id, switches[1]["id"], switches[3]["id"])
            links.append({"from": switches[1]["name"], "to": switches[3]["name"], "id": link5.get("link_id")})
            
            # Connect distribution switches to each other
            link6 = await link_nodes(lab_id, switches[2]["id"], switches[3]["id"])
            links.append({"from": switches[2]["name"], "to": switches[3]["name"], "id": link6.get("link_id")})
        
        # Connect access switches (if we have them)
        if len(switches) >= 6:
            # Connect distribution to access
            link7 = await link_nodes(lab_id, switches[2]["id"], switches[4]["id"])
            links.append({"from": switches[2]["name"], "to": switches[4]["name"], "id": link7.get("link_id")})
            
            link8 = await link_nodes(lab_id, switches[2]["id"], switches[5]["id"])
            links.append({"from": switches[2]["name"], "to": switches[5]["name"], "id": link8.get("link_id")})
            
            link9 = await link_nodes(lab_id, switches[3]["id"], switches[4]["id"])
            links.append({"from": switches[3]["name"], "to": switches[4]["name"], "id": link9.get("link_id")})
            
            link10 = await link_nodes(lab_id, switches[3]["id"], switches[5]["id"])
            links.append({"from": switches[3]["name"], "to": switches[5]["name"], "id": link10.get("link_id")})
            
            # Connect access switches to each other
            link11 = await link_nodes(lab_id, switches[4]["id"], switches[5]["id"])
            links.append({"from": switches[4]["name"], "to": switches[5]["name"], "id": link11.get("link_id")})
        
        return {
            "lab_id": lab_id,
            "title": title,
            "switches": switches,
            "links": links,
            "status": "success",
            "message": f"Created STP lab with {len(switches)} switches, each having {interfaces_per_switch} interfaces"
        }
    except Exception as e:
        return _handle_api_error("create_stp_lab", e)


@mcp.tool()
async def create_ospf_lab(title: str = "OSPF Network Lab", description: str = "Two routers connected via OSPF") -> Dict[str, Any]:
    """
    Create a complete OSPF lab with two routers properly configured
    
    Args:
        title: Title for the lab (default: "OSPF Network Lab")
        description: Lab description (default: "Two routers connected via OSPF")
    
    Returns:
        Dictionary with lab ID, router IDs, and access instructions
    """
    auth_check = _check_auth()
    if auth_check:
        return auth_check
    
    try:
        # Create the lab
        lab_response = await create_lab(title, description)
        if "error" in lab_response:
            return lab_response
        
        lab_id = lab_response["lab_id"]
        
        # Create two routers
        router1_result = await create_router(lab_id, "Router1", 50, 50)
        if "error" in router1_result:
            return {"error": f"Failed to create Router1: {router1_result['error']}"}
        
        router2_result = await create_router(lab_id, "Router2", 200, 50)
        if "error" in router2_result:
            return {"error": f"Failed to create Router2: {router2_result['error']}"}
        
        # Connect the routers
        link_result = await link_nodes(lab_id, router1_result["node_id"], router2_result["node_id"])
        if "error" in link_result:
            return {"error": f"Failed to link routers: {link_result['error']}"}
        
        # Configure Router1 with OSPF
        router1_config = """
! Basic Router1 Configuration with OSPF
!
hostname Router1
!
interface GigabitEthernet0/0
 ip address 10.0.0.1 255.255.255.0
 no shutdown
!
router ospf 1
 network 10.0.0.0 0.0.0.255 area 0
!
"""
        
        await configure_node(lab_id, router1_result["node_id"], router1_config)
        
        # Configure Router2 with OSPF
        router2_config = """
! Basic Router2 Configuration with OSPF
!
hostname Router2
!
interface GigabitEthernet0/0
 ip address 10.0.0.2 255.255.255.0
 no shutdown
!
router ospf 1
 network 10.0.0.0 0.0.0.255 area 0
!
"""
        
        await configure_node(lab_id, router2_result["node_id"], router2_config)
        
        return {
            "lab_id": lab_id,
            "title": title,
            "router1_id": router1_result["node_id"],
            "router2_id": router2_result["node_id"],
            "link_id": link_result.get("link_id"),
            "status": "success",
            "instructions": "Lab created with OSPF routing between Router1 (10.0.0.1) and Router2 (10.0.0.2). Start the lab to test connectivity."
        }
    except Exception as e:
        return _handle_api_error("create_ospf_lab", e)


# Configuration Templates

@mcp.resource("cml://templates/basic-router")
def basic_router_template() -> str:
    """Basic router configuration template"""
    return """
! Basic Router Configuration Template
!
hostname {{hostname}}
!
interface GigabitEthernet0/0
 ip address {{interface_ip}} {{interface_mask}}
 no shutdown
!
"""


@mcp.resource("cml://templates/basic-switch")
def basic_switch_template() -> str:
    """Basic switch configuration template"""
    return """
! Basic Switch Configuration Template
!
hostname {{hostname}}
!
vlan {{vlan_id}}
 name {{vlan_name}}
!
"""


@mcp.resource("cml://templates/ospf-config")
def ospf_template() -> str:
    """OSPF configuration template"""
    return """
! OSPF Configuration Template
!
router ospf {{process_id}}
 network {{network_address}} {{wildcard_mask}} area {{area_id}}
!
"""


@mcp.prompt("cml-describe-topology")
def describe_topology_prompt(lab_id: str) -> str:
    """Prompt for describing a lab topology"""
    return f"""Please analyze the following network topology from Cisco Modeling Labs (Lab ID: {lab_id}).
Describe the network elements, their connections, and the overall architecture.
Suggest any improvements or potential issues with the design.
"""


@mcp.prompt("cml-create-lab")
def create_lab_prompt() -> str:
    """Prompt for creating a new lab"""
    return """I need you to help me create a network lab in Cisco Modeling Labs.

Please design a lab that meets the following requirements:
{{requirements}}

For each device, specify:
1. Device type (router, switch, etc.)
2. Basic configuration
3. Network connections

After designing the topology, you'll need to:
1. Create the lab in CML
2. Add the nodes
3. Create the links between nodes
4. Configure each node
5. Start the lab

Please walk through this process step by step.
"""


# Main entry point
if __name__ == "__main__":
    mcp.run()