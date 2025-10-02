# HTTP Health Check Plugin

This plugin performs HTTP/HTTPS health checks on configured URLs and reports the status back to the main tray application.

## Features

- HTTP/HTTPS requests with configurable timeout
- Status code validation (default: 200)
- Response text validation (optional)
- No external dependencies (uses Python's built-in `urllib`)
- Configurable check frequency
- Thread-safe operation

## Configuration

Create a `config/http_health.json` file with the following structure:

```json
{
    "config": {
        "frequency_in_sec": 300
    },
    "urls": [
        {
            "url": "https://www.example.com",
            "timeout": 10,
            "expected_status": 200,
            "expected_text": "Welcome"
        }
    ]
}
```

### Configuration Options

- `config.frequency_in_sec`: How often to run health checks (in seconds)
- `urls[].url`: The URL to check (HTTP or HTTPS)
- `urls[].timeout`: Request timeout in seconds (default: 30)
- `urls[].expected_status`: Expected HTTP status code (default: 200)
- `urls[].expected_text`: Optional text that must be present in the response

## Status Codes

- **Green (G)**: All checks passed
- **Red (R)**: One or more checks failed
- **Unknown (?)**: Error occurred during checking

## Usage

1. Copy `config/http_health.sample.json` to `config/http_health.json`
2. Modify the configuration to match your requirements
3. Start the main application
4. Click "HTTP Health Check" in the tray menu to enable/disable monitoring

The plugin will run in a background thread and update the tray icon color based on the health status.