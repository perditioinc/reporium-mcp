FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# stdio MCP server — invoked by MCP clients over stdio (no network port).
CMD ["python", "mcp_server.py"]
