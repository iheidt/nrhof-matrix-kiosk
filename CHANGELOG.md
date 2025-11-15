# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-11-07

### Added
- **Worker Base Class**: Unified base class for all background workers (AudioWorker, WakeWordWorker, SongRecognitionWorker)
  - Eliminates ~150 lines of duplicate code
  - Standardizes lifecycle management (start/stop/hooks)
  - Consistent logging and error handling
- **Event Bus Dependency Injection**: Event bus can now be injected into workers, scenes, and localization
  - Improves testability (can inject mock event bus)
  - Enables isolated unit testing
  - Maintains backward compatibility with global instance
- **Scene Controller Injection**: Routing layer no longer directly imports SceneManager
  - Breaks circular dependency between routing and scenes
  - Intent handlers use injected scene controller
  - Enables testing with mock scene controllers
- **Renderer Interface Documentation**: Clear contract for renderer implementations
  - Distinguishes required vs optional methods
  - Documents backward compatibility strategy
  - Enables future renderer backends (Metal, headless)
- **Font System Documentation**: Comprehensive documentation for font loading and rendering
  - Organized into logical sections
  - Documents public API and internal functions
  - Explains mixed-font rendering for Japanese
- **Development Tooling**:
  - Black formatter configuration (line length 100)
  - Ruff linter with comprehensive rules
  - MyPy type checker configuration
  - Pytest test framework setup
  - Makefile with fmt, lint, type, test, cov, check targets
  - VS Code launch and task configurations
- **CI/CD Pipeline**: GitHub Actions workflow for automated checks
  - Runs on all PRs and pushes to dev/main
  - Linting (ruff), formatting (black), type checking (mypy)
  - Smoke tests to verify imports
- **Test Suite**: 10 unit tests covering refactored seams
  - Event bus DI and isolation
  - Worker base class lifecycle
  - Routing/scenes decoupling
  - Renderer interface contract

### Fixed
- Circular import dependency between `routing/` and `scenes/` modules
- Bare `except:` clauses replaced with explicit `except Exception:`
- Import organization (moved imports to top of files)
- Dead code removal (unreachable return statements)

### Changed
- All workers now inherit from `BaseWorker`
- RendererBase.render() and present() are now optional (non-abstract)
- Intent handlers use dependency injection instead of direct imports
- Font system organized with clear section comments

### Technical Debt Reduced
- ~150 lines of duplicate code removed
- 1 circular dependency eliminated
- Improved separation of concerns
- Better testability throughout codebase

### Metrics
- Files modified: ~75
- Tests added: 10 (all passing)
- Code coverage: Core seams validated
- Performance: No regression (59 FPS maintained)
- Breaking changes: 0 (100% backward compatible)

## [0.1.0] - Previous

Initial release with core bot functionality.

---

[0.2.0]: https://github.com/dasheidt/nrhof-bot/compare/v0.1.0...v0.2.0
