# Development Guide

## Overview

This guide provides comprehensive information for developers working on the Gelatinous MUD project. It covers our development philosophy, coding standards, contribution guidelines, and best practices for maintaining the codebase.

## Development Philosophy

### Core Principles

**1. Roleplay-First Design**
- Every feature should enhance storytelling and character interaction
- Combat serves the narrative, not vice versa
- Player agency and meaningful choices are paramount
- Default to non-violent resolution when possible

**2. Evennia-Native Development**
- Leverage Evennia's built-in tools and patterns
- Follow platform conventions for Scripts, Handlers, and Commands
- Use Evennia's typeclass system effectively
- Maintain compatibility with Evennia's core functionality

**3. Clean Architecture**
- Modular design with clear separation of concerns
- Python best practices throughout the codebase
- Predictable structure for AI-assisted development
- Open source community standards

### Decision-Making Priority Order

When making technical decisions, follow this priority hierarchy:

1. **Python Best Practices** - Clean, readable, maintainable code
2. **Evennia Best Practices** - Platform-native development patterns
3. **AI-Driven Development** - Predictable structure for AI assistance
4. **Open Source Community** - Easy contribution and understanding

## Code Standards

### Python Coding Standards

**PEP 8 Compliance**
- Use 4 spaces for indentation (no tabs)
- Line length maximum of 88 characters (Black formatter standard)
- Use descriptive variable and function names
- Follow Python naming conventions (snake_case, PascalCase, etc.)

**Documentation Requirements**
```python
def example_function(param1: str, param2: int) -> bool:
    """
    Brief description of what the function does.
    
    Args:
        param1: Description of first parameter
        param2: Description of second parameter
        
    Returns:
        Description of return value
        
    Raises:
        ExceptionType: Description of when this exception is raised
    """
    pass
```

**Type Hints**
- Use type hints for all function parameters and return values
- Import types from `typing` module when needed
- Use `Optional` for parameters that can be None
- Document complex types clearly

### Diagrams in Specs

Use [Mermaid](https://mermaid.js.org/) (`\`\`\`mermaid` code fences) for all architectural, flow, sequence, and state diagrams. GitHub renders these natively.

**Use Mermaid for:**
- Architecture overviews, system flowcharts, state machines
- Data flow diagrams, dependency graphs, timelines/Gantt charts
- Sequence diagrams showing component interactions

**Keep plain code fences for:**
- In-game UI mockups (terminal output, ASCII art the player sees)
- Object hierarchy / data structure illustrations with attribute annotations
- Directory tree listings

```mermaid
graph LR
    A["Source System"] --> B{"Signal Bus"}
    B --> C["Layer"]
    C --> D[/"Score"\]
```

### Constants and Magic Numbers

**Constants System**
- All magic strings and numbers must be defined in appropriate constants files
- Use descriptive names that indicate purpose and context
- Group related constants together
- Include comments explaining non-obvious values

```python
# world/combat/constants.py
MSG_ATTACK_SUCCESS = "|gYou strike {target} with {weapon}!|n"
MSG_ATTACK_MISS = "|yYou miss {target} with your attack.|n"
DEFAULT_GRIT = 1
GRAPPLE_DIFFICULTY = 8
```

**Avoiding Magic Numbers**
```python
# Bad
if roll_result >= 8:
    success = True

# Good
if roll_result >= constants.GRAPPLE_DIFFICULTY:
    success = True
```

### Error Handling

**Comprehensive Error Handling**
- Use try-except blocks for operations that might fail
- Log errors with appropriate detail level
- Provide meaningful error messages to users
- Fail gracefully without breaking the system

```python
from world.combat.utils import log_combat_action

try:
    result = risky_operation()
except SpecificException as e:
    log_combat_action(f"Operation failed: {e}", level="ERROR")
    caller.msg("Something went wrong. Please try again.")
    return False
```

**Debug Logging**
- Use consistent debug prefixes for different systems
- Include relevant context in log messages
- Use appropriate logging levels (DEBUG, INFO, WARNING, ERROR)
- Disable verbose logging in production

### Utility Functions

**Reusable Code**
- Extract common operations into utility functions
- Use the existing `world.combat.utils` module
- Create new utility modules for non-combat systems
- Document utility functions thoroughly

```python
# world/combat/utils.py
def get_numeric_stat(character, stat_name: str, default: int = 1) -> int:
    """
    Safely retrieve a numeric stat from a character.
    
    Args:
        character: The character object
        stat_name: Name of the stat to retrieve
        default: Default value if stat is invalid
        
    Returns:
        The stat value as an integer
    """
    stat_value = getattr(character, stat_name, default)
    return stat_value if isinstance(stat_value, (int, float)) else default
```

## Module Organization

### Combat Commands Structure

**File Organization**
```
commands/combat/
├── core_actions.py      # Fundamental combat actions
├── movement.py          # Movement and positioning
├── special_actions.py   # Advanced tactical actions
├── info_commands.py     # Information and awareness
└── cmdset_combat.py     # Command set definition
```

**Command Class Structure**
```python
class CmdExample(Command):
    """
    Brief description of what the command does.
    
    Usage:
        example <target>
        example/option <target>
    
    This command allows players to...
    """
    
    key = "example"
    aliases = ["ex"]
    locks = "cmd:all()"
    help_category = "Combat"
    
    def func(self):
        """Main command logic."""
        # Input validation
        if not self.args:
            self.caller.msg(constants.MSG_EXAMPLE_NO_TARGET)
            return
            
        # Business logic
        target = self.caller.search(self.args.strip())
        if not target:
            return
            
        # Execute action
        result = self.execute_example_action(target)
        
        # Provide feedback
        self.caller.msg(f"You example {target}.")
    
    def execute_example_action(self, target):
        """Separate business logic for testability."""
        # Actual implementation here
        pass
```

### World Systems Structure

**Combat System Organization**
```
world/combat/
├── constants.py         # All combat constants
├── utils.py            # Utility functions
├── handler.py          # Main combat handler
├── proximity.py        # Proximity management
├── grappling.py        # Grappling system
└── messages/           # Message templates
```

**Handler Pattern**
```python
class CombatHandler(DefaultScript):
    """
    Main combat handler following Evennia Script pattern.
    
    Manages combat state, turn processing, and cleanup.
    """
    
    def at_script_creation(self):
        """Initialize combat handler."""
        super().at_script_creation()
        # Setup code here
        
    def at_repeat(self):
        """Process combat turns."""
        # Main combat loop
        
    def at_stop(self):
        """Clean up when combat ends."""
        # Cleanup code here
```

## Testing Guidelines

### Unit Testing

**Test Structure**
```python
# tests/test_combat_utils.py
import unittest
from unittest.mock import Mock, patch
from world.combat.utils import get_numeric_stat

class TestCombatUtils(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.mock_character = Mock()
        
    def test_get_numeric_stat_valid(self):
        """Test retrieving valid numeric stat."""
        self.mock_character.grit = 5
        result = get_numeric_stat(self.mock_character, "grit")
        self.assertEqual(result, 5)
        
    def test_get_numeric_stat_invalid(self):
        """Test retrieving invalid stat returns default."""
        self.mock_character.grit = "invalid"
        result = get_numeric_stat(self.mock_character, "grit", default=1)
        self.assertEqual(result, 1)
```

**Test Coverage**
- Aim for >80% test coverage on critical systems
- Test both success and failure paths
- Mock external dependencies appropriately
- Write integration tests for complex workflows

### Manual Testing

**Test Scenarios**
- Create comprehensive test scenarios for combat features
- Test edge cases and error conditions
- Verify backward compatibility after changes
- Test with multiple players and complex scenarios

## Contribution Guidelines

### Pull Request Process

**Before Submitting**
1. Ensure all tests pass
2. Update documentation for any changes
3. Follow the established code style
4. Add appropriate debug logging
5. Verify backward compatibility

**Pull Request Description**
- Clearly describe what the PR does
- Explain why the change is needed
- List any breaking changes
- Include testing instructions
- Reference related issues

### Code Review Standards

**Review Checklist**
- [ ] Code follows established patterns
- [ ] Documentation is updated
- [ ] Tests are included and passing
- [ ] Error handling is appropriate
- [ ] Constants are used instead of magic values
- [ ] Utility functions are leveraged where appropriate

## Debugging and Troubleshooting

### Debug Infrastructure

**Logging System**
```python
from world.combat.utils import log_combat_action

# Different log levels
log_combat_action("Debug information", level="DEBUG")
log_combat_action("Important information", level="INFO")
log_combat_action("Warning condition", level="WARNING")
log_combat_action("Error occurred", level="ERROR")
```

**Debug Prefixes**
- Use consistent prefixes for different systems
- Include relevant context in debug messages
- Make debug messages searchable and filterable

### Common Issues and Solutions

**NDB Attribute Persistence**
- Problem: NDB attributes persisting between sessions
- Solution: Use force-clearing with explicit False assignment
- Best Practice: Always validate NDB state before use

**SaverList Corruption**
- Problem: SaverList objects becoming corrupted
- Solution: Use defensive copying and validation
- Best Practice: Implement data access layer for SaverList operations

**Handler Cleanup**
- Problem: Combat handlers not cleaning up properly
- Solution: Implement comprehensive cleanup in `at_stop()` method
- Best Practice: Use try-finally blocks for critical cleanup

## Performance Considerations

### Optimization Guidelines

**Efficient Algorithms**
- Avoid O(n²) operations in combat processing
- Use appropriate data structures for the task
- Cache expensive calculations when possible
- Minimize database queries in tight loops

**Memory Management**
- Clean up temporary objects promptly
- Use weak references where appropriate
- Avoid deep copying large data structures
- Monitor memory usage during development

### Monitoring and Profiling

**Performance Metrics**
- Track combat handler creation/destruction
- Monitor memory usage over time
- Measure response times for complex operations
- Log performance warnings for slow operations

## Future Development

### Planned Features

**Short-Term Goals**
- Enhanced error handling and recovery
- Comprehensive test suite
- Performance optimization
- Additional combat actions

**Long-Term Vision**
- Service layer architecture
- Event-driven system
- Plugin architecture
- Advanced AI behaviors

### Architecture Evolution

**Service Layer**
```python
# Future service layer example
class CombatService:
    def __init__(self, handler):
        self.handler = handler
        
    def initiate_attack(self, attacker, target):
        """High-level attack initiation."""
        # Validation, setup, execution
        pass
        
    def process_grapple(self, grappler, target):
        """Complex grappling logic."""
        # Grapple mechanics
        pass
```

**Event System**
```python
# Future event system example
class CombatEvent:
    def __init__(self, event_type, data):
        self.event_type = event_type
        self.data = data
        
class CombatEventBus:
    def publish(self, event):
        # Notify all subscribers
        pass
```

## Resources and References

### Evennia Documentation
- [Evennia Official Documentation](https://www.evennia.com/docs/)
- [Evennia Command System](https://www.evennia.com/docs/latest/Components/Commands.html)
- [Evennia Scripts](https://www.evennia.com/docs/latest/Components/Scripts.html)

### Python Resources
- [PEP 8 Style Guide](https://www.python.org/dev/peps/pep-0008/)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [Python Testing](https://docs.python.org/3/library/unittest.html)

### Project-Specific Documentation
- `PROJECT_OVERVIEW.md` - Project overview and philosophy
- `ARCHITECTURE.md` - File structure and architectural decisions
- `specs/COMBAT_SYSTEM.md` - Combat system documentation
- Module-specific README files

---

*This development guide is a living document that evolves with the project. When in doubt, follow the established patterns and ask for clarification. The goal is to maintain high code quality while preserving the project's roleplay-first philosophy.*
