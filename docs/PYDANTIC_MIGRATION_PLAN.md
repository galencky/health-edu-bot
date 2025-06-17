# Pydantic v2 Migration Plan

## Why Migrate?

Current issues with dict-based sessions:
- **No type safety** - `session['stt_last_translation']` vs `session['stt_last_tanslation']` fails silently
- **No IDE support** - No autocomplete, no type hints
- **No validation** - Can set invalid values
- **Hard to refactor** - String keys scattered across codebase
- **No documentation** - Field purposes unclear

Benefits of Pydantic v2:
- **Type safety** - Compile-time and runtime validation
- **IDE support** - Full autocomplete and type checking
- **Performance** - Pydantic v2 is faster than dict access
- **Documentation** - Self-documenting with field descriptions
- **Serialization** - Built-in JSON/dict conversion

## Migration Strategy

### Phase 1: Create Models (DONE ✅)
- Created `UserSession` model with all fields
- Backward compatible with `to_legacy_dict()` and `from_legacy_dict()`
- `SessionProxy` for gradual migration

### Phase 2: Update Session Manager (1 day)
```python
# In session_manager.py
from models.session import UserSession, SessionProxy

def _create_new_session() -> dict:
    """Create a new session with default values"""
    # Option 1: Return Pydantic model as dict
    return UserSession().to_legacy_dict()
    
    # Option 2: Return SessionProxy for dual access
    # return SessionProxy(UserSession().to_legacy_dict())
```

### Phase 3: Migrate Read-Only Access (2-3 days)
Start with safe, read-only operations:

```python
# Before
if session.get("started"):
    mode = session.get("mode")

# After
if session.started:
    mode = session.mode
```

Priority files:
1. `handlers/logic_handler.py` - Core logic
2. `handlers/line_handler.py` - Message handling
3. `handlers/medchat_handler.py` - Medical chat

### Phase 4: Migrate Write Operations (2-3 days)
Update session modifications:

```python
# Before
session["started"] = True
session["mode"] = "edu"

# After
session.started = True
session.mode = "edu"
```

### Phase 5: Add Validation (1 day)
Leverage Pydantic's validation:

```python
class UserSession(BaseModel):
    mode: Optional[Literal["edu", "chat"]] = None
    
    @field_validator('mode')
    def validate_mode(cls, v):
        if v not in [None, "edu", "chat"]:
            raise ValueError(f"Invalid mode: {v}")
        return v
```

### Phase 6: Cleanup (1 day)
- Remove dict access patterns
- Remove `SessionProxy` wrapper
- Update tests

## Implementation Example

Here's how to start using it today:

```python
# handlers/session_manager.py
from models.session import UserSession

# Keep dict storage for now, but use models internally
_sessions: Dict[str, UserSession] = {}

def get_user_session(user_id: str) -> UserSession:
    """Get or create a user session with type safety"""
    with _global_lock:
        if user_id not in _sessions:
            _sessions[user_id] = UserSession(user_id=user_id)
        
        session = _sessions[user_id]
        session.last_accessed = datetime.now()
        return session

# For backward compatibility during migration
def get_user_session_dict(user_id: str) -> dict:
    """Legacy dict interface"""
    return get_user_session(user_id).to_legacy_dict()
```

## Quick Wins

1. **Start with new features** - Use Pydantic for any new session fields
2. **Type hints** - Add type hints even before full migration:
   ```python
   def handle_education(session: dict) -> str:  # Change to UserSession later
   ```
3. **Validation** - Add validation for critical fields like email, language codes
4. **IDE support** - Get immediate autocomplete benefits

## Risk Mitigation

1. **Gradual migration** - Use `SessionProxy` to support both patterns
2. **Feature flags** - Add `USE_PYDANTIC_SESSIONS` environment variable
3. **Extensive testing** - Test both dict and model access patterns
4. **Rollback plan** - Keep `to_legacy_dict()` for quick rollback

## Timeline

- Week 1: Implement SessionProxy, migrate session_manager.py
- Week 2: Migrate read operations in handlers
- Week 3: Migrate write operations, add validation
- Week 4: Testing, cleanup, documentation

## Conclusion

Migrating to Pydantic v2 is:
- **Feasible** - Already using Pydantic v2.11.5
- **Low risk** - Can be done gradually with backward compatibility
- **High value** - Prevents bugs, improves developer experience
- **Recommended** - Start with SessionProxy for zero-downtime migration