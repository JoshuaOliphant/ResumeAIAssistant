# Stream JSON Processing Fix

## Problem Identified

The logs showed repeated errors:
```
Error processing stream JSON: 'list' object has no attribute 'strip'
```

This occurred because the Claude Code stream JSON output sometimes sends `content` as a list instead of a string, but our code was trying to call `.strip()` on it.

## Root Cause

In the `_process_stream_json` method, the code assumed `content` would always be a string:

```python
# BEFORE (causing errors)
content = parsed.get("content", "")
if content.strip():  # This fails if content is a list
    log_streamer.add_log(...)
```

## Solution Implemented

Added type checking and conversion in multiple locations:

### 1. **Content Event Handler** (line ~399)
```python
if event_type == "content":
    content = parsed.get("content", "")
    # Handle case where content might be a list
    if isinstance(content, list):
        content = " ".join(str(item) for item in content)
    elif not isinstance(content, str):
        content = str(content)
        
    if content.strip():
        log_streamer.add_log(...)
```

### 2. **Tool Result Handler** (line ~426)
```python
elif event_type == "tool_result":
    result = parsed.get("content", "")
    
    # Handle case where result might be a list or non-string
    if isinstance(result, list):
        result = " ".join(str(item) for item in result)
    elif not isinstance(result, str):
        result = str(result)
```

### 3. **Generic Event Handler** (line ~492)
```python
else:
    if "content" in parsed:
        content = parsed.get("content", "")
        # Handle case where content might be a list or non-string
        if isinstance(content, list):
            content = " ".join(str(item) for item in content)
        elif not isinstance(content, str):
            content = str(content)
            
        if content.strip():
            log_streamer.add_log(...)
```

### 4. **Fallback Processing** (line ~984)
```python
if "content" in parsed:
    content = parsed.get("content", "")
    # Handle case where content might be a list or non-string
    if isinstance(content, list):
        content = " ".join(str(item) for item in content)
    elif not isinstance(content, str):
        content = str(content)
        
    if content.strip():
        log_streamer.add_log(...)
```

## Testing Results

All content types now handle correctly:

- ✅ **String content**: `"This is a string"` → processed normally
- ✅ **List content**: `["This", "is", "a", "list"]` → converted to `"This is a list"`
- ✅ **Number content**: `42` → converted to `"42"`

## Benefits

1. **Eliminates Error Spam**: No more repeated "list object has no attribute 'strip'" errors
2. **Robust Processing**: Handles unexpected data types gracefully
3. **Better Logging**: All content types are properly logged
4. **Maintained Functionality**: Existing string processing continues to work normally

## Files Modified

- `app/services/claude_code/executor.py`: Updated `_process_stream_json` method with type-safe content processing

The fix ensures that regardless of whether Claude Code sends content as a string, list, or other data type, the stream processing will handle it gracefully without errors.