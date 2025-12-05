# API Reference

The Geo Assistant API provides a streaming chat endpoint for geographic queries.

## Base URL

```
http://localhost:8000
```

## Endpoint

### POST /chat

Stream chat responses from the geographic assistant agent.

**Request Body**

```json
{
  "thread_id": "uuid-string",
  "agent_state_input": {
    "messages": [
      {
        "type": "human",
        "content": "Your question here"
      }
    ]
  }
}
```

**Schema**

- `thread_id` (string): UUID for conversation thread
- `agent_state_input` (object):
  - `messages` (array): Array of message objects with `type` and `content`

**Response**

Streaming NDJSON format (`application/x-ndjson`). Each line contains:

```json
{
  "thread_id": "uuid-string",
  "state": {
    "messages": [...],
    "place": {...},
    "search_area": {...},
    "naip_img_bytes": {...}
  }
}
```

**Example**

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "123e4567-e89b-12d3-a456-426614174000",
    "agent_state_input": {
      "messages": [{"type": "human", "content": "Your question"}]
    }
  }'
```

**Python Example**

```python
import json
import uuid
import httpx

thread_id = str(uuid.uuid4())

request_body = {
    "thread_id": thread_id,
    "agent_state_input": {
        "messages": [{"type": "human", "content": "Your question"}]
    },
}

with httpx.stream(
    "POST",
    "http://localhost:8000/chat",
    json=request_body,
    timeout=360.0,
) as response:
    response.raise_for_status()
    
    for line in response.iter_lines():
        if not line:
            continue
        
        data = json.loads(line)
        state = data.get("state", {})
        messages = state.get("messages", [])
        
        # Process messages
        for msg in messages:
            print(f"{msg['type']}: {msg['content']}")

        # Process state updates
        # ...
```