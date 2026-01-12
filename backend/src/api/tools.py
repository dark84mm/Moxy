"""
Tool definitions for OpenAI Completions API.
These tools are used by the agent endpoints.
"""
import os
import asyncio
import logging
import sqlite3
from .. import db, state, http_sender, proxy_manager, browser_manager
from browser_use import Agent as BrowserAgent, ChatOpenAI, ChatOllama

logger = logging.getLogger(__name__)


def get_query_database_tool():
    """Get the query_database tool definition for OpenAI Completions API."""
    return {
        "type": "function",
        "function": {
            "name": "query_database",
            "description": """Execute SQL SELECT queries against the HTTP requests database.

Database schema (requests table):
- id: INTEGER PRIMARY KEY - Unique request ID
- method: TEXT NOT NULL - HTTP method (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS)
- url: TEXT NOT NULL - Full URL including path (e.g., "https://example.com/api/users")
- raw_request: TEXT - Full HTTP request as string
- raw_response: TEXT - Full HTTP response as string  
- status_code: INTEGER - HTTP response status code (200, 404, 500, etc.)
- duration_ms: INTEGER - Request duration in milliseconds
- timestamp: TEXT NOT NULL - Request timestamp in ISO format (e.g., "2024-01-01T12:00:00"), use for ordering
- completed_at: TEXT - Response completion timestamp in ISO format
- flow_id: TEXT - Proxy flow identifier

Common query patterns:
- Filter by method: WHERE method = 'GET'
- Filter by URL: WHERE url LIKE '%login%'
- Filter by status: WHERE status_code = 404
- Order by time: ORDER BY timestamp DESC (newest first) or ORDER BY timestamp ASC (oldest first)
- Limit results: LIMIT 10
- Combine filters: WHERE method = 'POST' AND url LIKE '%api%' ORDER BY timestamp DESC LIMIT 5

Examples:
- "SELECT * FROM requests WHERE method = 'GET' ORDER BY timestamp DESC LIMIT 10"
- "SELECT * FROM requests WHERE url LIKE '%login%' ORDER BY timestamp DESC LIMIT 5"
- "SELECT * FROM requests WHERE status_code = 404 ORDER BY timestamp DESC"
- "SELECT * FROM requests WHERE method = 'POST' AND url LIKE '%api%' ORDER BY timestamp ASC LIMIT 1"
- "SELECT * FROM requests ORDER BY timestamp ASC LIMIT 1" (first/oldest request)
- "SELECT * FROM requests ORDER BY timestamp DESC LIMIT 10" (last 10/recent requests)

When user asks for specific requests, construct a SQL SELECT query. Use LIKE for URL searches, = for exact matches (method, status_code). Always use ORDER BY timestamp with appropriate LIMIT.""",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql_query": {
                        "type": "string",
                        "description": """A SQL SELECT query to execute. Only SELECT queries are allowed.
Build queries based on what the user asks:
- User says "GET requests" → SELECT * FROM requests WHERE method = 'GET' ORDER BY timestamp DESC LIMIT 100
- User says "first request" → SELECT * FROM requests ORDER BY timestamp ASC LIMIT 1
- User says "last 10 requests" → SELECT * FROM requests ORDER BY timestamp DESC LIMIT 10
- User says "login requests" → SELECT * FROM requests WHERE url LIKE '%login%' ORDER BY timestamp DESC LIMIT 100
- User says "POST /api/login" → SELECT * FROM requests WHERE method = 'POST' AND url LIKE '%/api/login%' ORDER BY timestamp DESC LIMIT 100
- User says "status 404" → SELECT * FROM requests WHERE status_code = 404 ORDER BY timestamp DESC LIMIT 100

Always include ORDER BY timestamp (DESC for newest/recent, ASC for oldest/first) and appropriate LIMIT."""
                    }
                },
                "required": ["sql_query"]
            }
        }
    }


def get_send_request_tool():
    """Get the send_request tool definition for OpenAI Completions API."""
    return {
        "type": "function",
        "function": {
            "name": "send_request",
            "description": """Send a raw HTTP request to a specified host and port.

This tool allows you to send HTTP requests similar to the resender functionality. You can send GET, POST, PUT, DELETE, PATCH, or any other HTTP method.

The raw_request should be a complete HTTP request string in the following format:
```
GET /api/users HTTP/1.1
Host: example.com
Content-Type: application/json

[optional body]
```

For POST/PUT/PATCH requests with a body:
```
POST /api/users HTTP/1.1
Host: example.com
Content-Type: application/json

{"name": "John", "email": "john@example.com"}
```

The host, port, and use_https parameters allow you to specify where to send the request.
- host: The target hostname (e.g., "example.com", "api.example.com")
- port: The target port (default: "443" for HTTPS, "80" for HTTP)
- use_https: Whether to use HTTPS (default: True unless port is "80")

Returns the HTTP response including status_code, headers, raw_response, and any error.""",
            "parameters": {
                "type": "object",
                "properties": {
                    "raw_request": {
                        "type": "string",
                        "description": "The raw HTTP request string. Must include the request line (METHOD PATH HTTP/VERSION), headers, and optional body separated by newlines."
                    },
                    "host": {
                        "type": "string",
                        "description": "The target hostname (e.g., 'example.com', 'api.example.com'). Default: 'example.com'"
                    },
                    "port": {
                        "type": "string",
                        "description": "The target port. Default: '443' for HTTPS, '80' for HTTP"
                    },
                    "use_https": {
                        "type": "boolean",
                        "description": "Whether to use HTTPS. Default: True unless port is '80'"
                    }
                },
                "required": ["raw_request"]
            }
        }
    }


def get_browse_tool():
    """Get the browse tool definition for OpenAI Completions API."""
    return {
        "type": "function",
        "function": {
            "name": "browse",
            "description": """Browse the web using an automated browser.

This tool allows you to control a browser to navigate websites, interact with pages, search for information, and perform various browsing tasks. The browser uses a proxy to capture all HTTP requests and responses.

The tool will automatically:
- Start the proxy if it's not running
- Create a browser session if one doesn't exist
- Execute the browsing task using an AI agent

You can provide a task description and optionally additional tasks to execute sequentially.

Examples:
- "search for dogs" - Search for dogs on a search engine
- "go to example.com and click the login button"
- "navigate to https://example.com and fill out the contact form"

Returns status and result message.""",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "The browsing task to execute. Describe what you want the browser to do, e.g., 'search for dogs', 'go to example.com', 'click the login button'"
                    },
                    "additional_tasks": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "Optional list of additional tasks to execute sequentially after the initial task"
                    }
                },
                "required": ["task"]
            }
        }
    }


def query_database(sql_query: str) -> dict:
    """
    Execute a SQL query against the requests database.
    
    Database schema (requests table):
    - id: INTEGER PRIMARY KEY - Unique request ID
    - method: TEXT NOT NULL - HTTP method (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS)
    - url: TEXT NOT NULL - Full URL including path (e.g., "https://example.com/api/users")
    - raw_request: TEXT - Full HTTP request as string
    - raw_response: TEXT - Full HTTP response as string
    - status_code: INTEGER - HTTP response status code (200, 404, 500, etc.)
    - duration_ms: INTEGER - Request duration in milliseconds
    - timestamp: TEXT NOT NULL - Request timestamp in ISO format (e.g., "2024-01-01T12:00:00")
    - completed_at: TEXT - Response completion timestamp in ISO format
    - flow_id: TEXT - Proxy flow identifier
    
    Examples:
    - SELECT * FROM requests WHERE method = 'GET' ORDER BY timestamp DESC LIMIT 10
    - SELECT * FROM requests WHERE url LIKE '%login%' ORDER BY timestamp DESC LIMIT 5
    - SELECT * FROM requests WHERE status_code = 404 ORDER BY timestamp DESC
    - SELECT * FROM requests WHERE method = 'POST' AND url LIKE '%api%' ORDER BY timestamp ASC LIMIT 1
    
    Args:
        sql_query: SQL SELECT query to execute (only SELECT queries allowed)
    
    Returns:
        A dict containing the query results: {"count": int, "requests": [...]}
    """
    try:
        project_id = state.get_current_project()
        if not project_id:
            return {"error": "No current project selected"}
        
        project = db.get_project_by_id(project_id)
        if not project:
            return {"error": "Project not found"}
        
        db_path = db.get_project_db_path(project['name'])
        if not os.path.exists(db_path):
            return {"count": 0, "requests": []}
        
        # Security: Only allow SELECT queries
        sql_query_upper = sql_query.strip().upper()
        if not sql_query_upper.startswith('SELECT'):
            return {"error": "Only SELECT queries are allowed"}
        
        # Use SQLite to execute query
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute(sql_query)
            rows = cursor.fetchall()
            
            # Convert rows to dicts
            result = [dict(row) for row in rows]
            
            return {
                "count": len(result),
                "requests": result
            }
        except sqlite3.Error as e:
            logger.error(f"SQL error: {e}")
            return {"error": f"SQL error: {str(e)}"}
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Error querying database: {e}", exc_info=True)
        return {"error": str(e)}


def send_request(raw_request: str, host: str = 'example.com', port: str = '443', use_https: bool = None) -> dict:
    """
    Send a raw HTTP request to a specified host.
    
    This function parses a raw HTTP request string and sends it to the specified host and port,
    similar to the resender functionality.
    
    Args:
        raw_request: Raw HTTP request string (e.g., "GET /api/users HTTP/1.1\\nHost: example.com\\n\\n")
        host: Target host (default: 'example.com')
        port: Target port (default: '443')
        use_https: Whether to use HTTPS (default: None, auto-determined from port - True unless port is '80')
    
    Returns:
        A dict containing the response: {
            "status_code": int,
            "headers": dict,
            "raw_response": str,
            "error": str (optional)
        }
    """
    try:
        # Auto-determine HTTPS if not specified
        if use_https is None:
            use_https = port != '80'
        
        # Send the request using http_sender
        result = http_sender.send_raw_http_request(raw_request, host, port, use_https)
        
        return result
    except Exception as e:
        logger.error(f"Error sending request: {e}", exc_info=True)
        return {
            "status_code": 0,
            "headers": {},
            "raw_response": f"Error: {str(e)}",
            "error": str(e)
        }


async def _browse_async(task: str, additional_tasks: list = None) -> dict:
    """
    Async helper function to browse using browser-use Agent.
    
    Args:
        task: Initial task for the browser agent
        additional_tasks: Optional list of additional tasks to execute
    
    Returns:
        A dict with the result: {"status": "success", "message": str, "error": str (optional)}
    """
    try:
        # Ensure proxy is running
        if not proxy_manager.is_proxy_running():
            logger.info("Proxy not running, starting proxy...")
            if not proxy_manager.start_proxy():
                return {"status": "error", "error": "Failed to start proxy"}
            # Wait a bit for proxy to start
            await asyncio.sleep(2)
        
        # Get or create browser session
        browser = await browser_manager.get_or_create_browser()
        
        # Select LLM and agent based on environment variables and BROWSER_USE_OPENAI
        use_ollama_env = os.environ.get("USE_OLLAMA", "false").lower()
        use_ollama = use_ollama_env not in ["false", "0", "no"]
        if use_ollama:
            llm = ChatOllama(
                model=os.environ.get("MODEL")
            )
        else:
            llm = ChatOpenAI(
                model=os.environ.get("MODEL", "gpt-5-mini"),
            )

        agent = BrowserAgent(
            task=task,
            browser_session=browser,
            llm=llm
        )
        
        # Run the initial task
        result = await agent.run()
        
        # Execute additional tasks if provided
        if additional_tasks:
            for additional_task in additional_tasks:
                agent.add_new_task(additional_task)
                result = await agent.run()
        
        return {
            "status": "success",
            "message": f"Completed task: {task}",
            "result": str(result) if result else "Task completed successfully"
        }
    except Exception as e:
        logger.error(f"Error browsing: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }


def browse(task: str, additional_tasks: list = None) -> dict:
    """
    Browse using browser-use Agent.
    
    This function ensures the proxy is running, gets or creates a browser session,
    and uses the Agent from browser_use to execute browsing tasks.
    
    Args:
        task: Initial task description (e.g., "search for dogs")
        additional_tasks: Optional list of additional tasks to execute sequentially
    
    Returns:
        A dict with the result: {"status": "success", "message": str, "error": str (optional)}
    """
    try:
        # Run async function in new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_browse_async(task, additional_tasks))
        finally:
            loop.close()
        return result
    except Exception as e:
        logger.error(f"Error running browse: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }
