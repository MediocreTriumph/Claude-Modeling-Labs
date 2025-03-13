# Claude Modeling Labs

A proof of concept tool for automating Cisco Modeling Labs (CML) using Claude AI.

## ⚠️ Warning: Proof of Concept

**This project is currently a proof of concept and is still under development.** 

Features may be incomplete, contain bugs, or change significantly between versions. Use at your own risk in non-production environments only.

## Overview

Claude Modeling Labs provides a set of tools that enable Claude AI to interact with Cisco Modeling Labs (CML) via its API. This allows Claude to create, configure, and manage network simulations in response to natural language requests.

The toolkit includes functions for:
- Lab management (create, list, start, stop)
- Node management (routers, switches, etc.)
- Link creation and management
- Device configuration
- Pre-built templates for common network scenarios

## Installation

### Prerequisites
- Python 3.8 or higher
- Cisco Modeling Labs (CML) 2.0 or higher
- Access to Claude AI or Claude function calling

### Installation on macOS

1. **Install Python (if not already installed)**:
   ```bash
   brew install python
   ```

2. **Clone the repository**:
   ```bash
   git clone https://github.com/MediocreTriumph/Claude-Modeling-Labs.git
   cd Claude-Modeling-Labs
   ```

3. **Set up a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

4. **Install dependencies**:
   ```bash
   pip install fastmcp httpx urllib3
   ```

### Installation on Windows

1. **Install Python (if not already installed)**:
   - Download and install from [python.org](https://www.python.org/downloads/windows/)
   - Ensure "Add Python to PATH" is checked during installation

2. **Clone the repository**:
   ```cmd
   git clone https://github.com/MediocreTriumph/Claude-Modeling-Labs.git
   cd Claude-Modeling-Labs
   ```

3. **Set up a virtual environment**:
   ```cmd
   python -m venv venv
   venv\Scripts\activate
   ```

4. **Install dependencies**:
   ```cmd
   pip install fastmcp httpx urllib3
   ```

## How It Works

This tool uses the FastMCP (Model Context Protocol) library to define a set of tools that Claude can use to interact with CML. These tools abstract the underlying API calls to provide a simpler interface for Claude to work with.

## Current Status

This project is still in early development. It successfully demonstrates the concept of allowing Claude to create and manage CML labs, but many features are still being refined.

## Limitations

- Error handling is basic
- Documentation is limited
- Not all CML features are exposed
- Security considerations are not fully addressed

## Next Steps

- Improve error handling and reporting
- Add more templates for common network scenarios
- Add support for more CML features
- Improve documentation
- Add proper authentication mechanisms

## Contributing

As this is a proof of concept, contributions are welcome but the project structure may change significantly. Please open an issue first to discuss any proposed changes.

## License

This project is available under the MIT License.