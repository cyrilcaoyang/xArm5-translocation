#!/usr/bin/env python3
"""
PyXArm CLI - Main entry point

Command-line interface for controlling xArm robots.

Usage:
    pyarm web [--host HOST] [--port PORT]
    pyarm --version
    pyarm --help

Commands:
    web         Start the web interface and API server
    
Options:
    --host HOST     Host to bind the server to [default: 0.0.0.0]
    --port PORT     Port to bind the server to [default: 6001]
    --version       Show version information
    --help          Show this help message
"""

import argparse
import os
import sys
from typing import List, Optional


def start_web_server(host: str = "0.0.0.0", port: int = 6001):
    """Start the web interface and API server."""
    print(f"🚀 Starting PyXArm Web Interface...")
    print(f"📡 Server: http://{host}:{port}")
    print(f"🌐 Web UI: http://{host}:{port}/web/")
    print(f"📖 API Docs: http://{host}:{port}/docs")
    print("=" * 50)
    
    # Set environment variables for the server
    os.environ["XARM_API_HOST"] = host
    os.environ["XARM_API_PORT"] = str(port)
    
    try:
        # Import and run the API server
        from src.core.xarm_api_server import app
        import uvicorn
        
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info"
        )
    except ImportError as e:
        print(f"❌ Error importing server components: {e}")
        print("💡 Make sure you're in the project directory and have installed dependencies")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)


def show_version():
    """Show version information."""
    try:
        from src.cli import __version__
        print(f"PyXArm CLI v{__version__}")
        print("Comprehensive xArm robot control package")
    except ImportError:
        print("PyXArm CLI (version unknown)")


def show_help():
    """Show help information."""
    print(__doc__)


def main(args: Optional[List[str]] = None):
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="pyarm",
        description="PyXArm - xArm robot control CLI",
        add_help=False  # We'll handle help ourselves
    )
    
    # Add subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Web command
    web_parser = subparsers.add_parser("web", help="Start the web interface")
    web_parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind the server to (default: 0.0.0.0)"
    )
    web_parser.add_argument(
        "--port",
        type=int,
        default=6001,
        help="Port to bind the server to (default: 6001)"
    )
    
    # Global options
    parser.add_argument("--version", action="store_true", help="Show version information")
    parser.add_argument("--help", action="store_true", help="Show help information")
    
    # Parse arguments
    if args is None:
        args = sys.argv[1:]
    
    parsed_args = parser.parse_args(args)
    
    # Handle global options
    if parsed_args.help or (not parsed_args.command and not parsed_args.version):
        show_help()
        return
    
    if parsed_args.version:
        show_version()
        return
    
    # Handle commands
    if parsed_args.command == "web":
        start_web_server(host=parsed_args.host, port=parsed_args.port)
    else:
        print(f"❌ Unknown command: {parsed_args.command}")
        print("💡 Use 'pyarm --help' for available commands")
        sys.exit(1)


if __name__ == "__main__":
    main() 