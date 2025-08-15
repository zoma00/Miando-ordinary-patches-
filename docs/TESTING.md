# Testing Guide for Miando Trading System

## Overview

This document provides comprehensive information about testing the Miando trading system, including automated testing, CI/CD practices, and quality assurance procedures.

## Table of Contents

1. [Testing Framework](#testing-framework)
2. [Test Structure](#test-structure)
3. [Running Tests](#running-tests)
4. [Continuous Integration](#continuous-integration)
5. [Test Categories](#test-categories)
6. [Performance Testing](#performance-testing)
7. [Contributing](#contributing)

## Testing Framework

The Miando trading system uses **pytest** as the primary testing framework, along with several plugins and tools:

- **pytest**: Main testing framework
- **pytest-cov**: Code coverage reporting
- **pytest-mock**: Mocking utilities
- **pytest-asyncio**: Async testing support
- **pytest-benchmark**: Performance benchmarking
- **factory-boy**: Test data generation
- **testcontainers**: Docker-based integration testing

## Test Structure

```
tests/
├── conftest.py              # Test configuration and fixtures
├── unit/                    # Unit tests
│   ├── test_common.py       # Common utilities tests
│   ├── test_ohlc_exporters.py  # OHLC exporter tests
│   └── ...
├── integration/             # Integration tests
│   └── test_complete_system.py  # End-to-end tests
├── performance/             # Performance tests
│   └── test_performance.py  # Benchmark tests
└── factories/               # Test data factories
    └── test_data.py         # Data generation utilities
```

## Running Tests

### Quick Start

```bash
# Run all tests
./run_tests.sh

# Or manually with pytest
pip install -r requirements-test.txt
pytest
```

### Test Categories

Run specific test categories using markers:

```bash
# Unit tests only
pytest -m unit

# Integration tests
pytest -m integration

# Database tests (requires running database)
pytest -m database

# Performance tests
pytest -m slow

# Docker tests
pytest -m docker
```

### With Coverage

```bash
# Generate coverage report
pytest --cov=patterns/json_split --cov-report=html

# View coverage report
open htmlcov/index.html
```

## Continuous Integration

The project uses GitHub Actions for CI/CD with the following pipeline:

### Pipeline Stages

1. **Code Quality Checks**
   - Black code formatting
   - Flake8 linting
   - MyPy type checking
   - Security scanning with Bandit

2. **Unit Tests**
   - Fast, isolated tests
   - Mock external dependencies
   - High code coverage requirements (>80%)

3. **Integration Tests**
   - Database integration
   - System component interaction
   - Real environment simulation

4. **Docker Tests**
   - Container build verification
   - Docker Compose integration
   - Multi-platform builds

5. **Performance Tests**
   - Benchmark execution times
   - Memory usage monitoring
   - Load testing scenarios

6. **Security Scanning**
   - Vulnerability detection
   - Dependency analysis
   - Container security

7. **Build and Deploy**
   - Docker image building
   - Multi-platform support
   - Production deployment (if configured)

### CI Configuration

The CI pipeline is defined in `.github/workflows/ci-cd.yml` and includes:

- **Triggers**: Push to main/develop, pull requests, scheduled runs
- **Matrix Testing**: Multiple Python versions and platforms
- **Parallel Execution**: Different test suites run concurrently
- **Artifact Storage**: Test reports, coverage, security scans

## Test Categories

### Unit Tests

**Purpose**: Test individual components in isolation

**Characteristics**:
- Fast execution (< 1 second per test)
- No external dependencies
- High code coverage
- Mock all external services

**Example**:
```python
def test_safe_float_with_valid_input():
    assert safe_float(42.5) == 42.5
    assert safe_float("42.5") == 42.5
```

### Integration Tests

**Purpose**: Test component interactions and system integration

**Characteristics**:
- Test real database interactions
- Verify data flow between components
- Test configuration and environment setup

**Example**:
```python
@pytest.mark.integration
def test_complete_export_cycle():
    success_count, failed_exporters = run_all_exporters_once("EURUSD")
    assert success_count == 5
```

### Performance Tests

**Purpose**: Ensure system meets performance requirements

**Characteristics**:
- Benchmark execution times
- Monitor memory usage
- Test under load conditions
- Validate scalability

**Example**:
```python
@pytest.mark.slow
def test_export_performance(benchmark):
    result = benchmark(run_all_exporters_once, "EURUSD")
    assert benchmark.stats['mean'] < 1.0  # Under 1 second
```

### Database Tests

**Purpose**: Validate database operations and schema

**Characteristics**:
- Test database connectivity
- Verify schema compliance
- Test data integrity
- Validate transactions

## Performance Testing

### Benchmarking

Performance tests use `pytest-benchmark` to measure:

- **Execution Time**: How fast operations complete
- **Memory Usage**: Memory consumption patterns
- **Throughput**: Operations per second
- **Scalability**: Performance under increasing load

### Load Testing

Simulates various load conditions:

- **Sustained Load**: Continuous operation over time
- **Burst Load**: Sudden spikes in activity
- **Concurrent Load**: Multiple operations simultaneously
- **Stress Testing**: Beyond normal operating conditions

### Performance Requirements

- **Export Cycle**: < 1 second for complete cycle
- **Database Queries**: < 100ms for typical queries
- **Memory Usage**: < 50MB per process
- **Concurrent Handling**: Support 10+ concurrent operations

## Code Quality Standards

### Coverage Requirements

- **Minimum Coverage**: 80% overall
- **Critical Components**: 90%+ coverage
- **New Code**: 100% coverage required

### Code Style

- **Formatting**: Black code formatter
- **Linting**: Flake8 with custom rules
- **Type Hints**: MyPy for type checking
- **Security**: Bandit security analysis

### Best Practices

1. **Test Naming**: Descriptive test names explaining what is tested
2. **AAA Pattern**: Arrange, Act, Assert structure
3. **Single Responsibility**: One concept per test
4. **Deterministic**: Tests should be repeatable and reliable
5. **Independent**: Tests should not depend on each other

## Test Environment Setup

### Local Development

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Start test database
docker-compose up -d miando-db

# Run tests
pytest
```

### Docker Testing

```bash
# Build and test containers
docker-compose build
docker-compose run --rm patterns python3 -m pytest

# Integration testing
docker-compose up -d
docker-compose run --rm patterns ./run_tests.sh
```

### CI Environment

The CI environment automatically:
- Sets up PostgreSQL test database
- Installs all dependencies
- Runs complete test suite
- Generates reports and artifacts

## Debugging Tests

### Running Specific Tests

```bash
# Single test file
pytest tests/unit/test_common.py

# Single test function
pytest tests/unit/test_common.py::test_safe_float_with_valid_input

# Tests matching pattern
pytest -k "test_database"
```

### Verbose Output

```bash
# Detailed output
pytest -v

# Even more details
pytest -vv

# Show local variables on failure
pytest -l
```

### Debug Mode

```bash
# Drop into debugger on failure
pytest --pdb

# Drop into debugger on first failure
pytest -x --pdb
```

## Contributing

### Before Submitting Code

1. **Run Tests**: Ensure all tests pass locally
2. **Check Coverage**: Maintain or improve coverage
3. **Code Quality**: Pass all quality checks
4. **Add Tests**: Include tests for new functionality

### Writing Tests

1. **Follow Patterns**: Use existing test patterns as examples
2. **Use Factories**: Leverage test data factories for realistic data
3. **Mock External**: Mock all external dependencies
4. **Document Intent**: Clear test names and docstrings

### Test Data

Use the test data factories in `tests/factories/test_data.py`:

```python
from tests.factories.test_data import OHLCDataFactory, AccountStateFactory

def test_with_realistic_data():
    ohlc_data = OHLCDataFactory.build()
    account_data = AccountStateFactory.build()
    # ... test logic
```

## Troubleshooting

### Common Issues

1. **Database Connection**: Ensure test database is running
2. **Import Errors**: Check PYTHONPATH and module structure
3. **Fixture Scope**: Understand fixture scoping for setup/teardown
4. **Mock Conflicts**: Ensure mocks don't interfere with each other

### Getting Help

- Check test logs and error messages
- Review existing similar tests
- Consult pytest documentation
- Ask team members for guidance

## Metrics and Reporting

### Test Metrics

The CI system tracks:
- **Test Success Rate**: Percentage of passing tests
- **Coverage Trends**: Coverage over time
- **Performance Trends**: Execution time trends
- **Flaky Tests**: Tests with inconsistent results

### Reports Generated

- **Coverage Report**: HTML coverage visualization
- **Performance Report**: Benchmark results
- **Security Report**: Vulnerability scan results
- **Test Report**: Detailed test execution results

## Future Improvements

### Planned Enhancements

1. **Property-Based Testing**: Using Hypothesis for edge case discovery
2. **Mutation Testing**: Using mutmut for test quality validation
3. **Visual Testing**: Screenshot comparison for UI components
4. **Chaos Engineering**: Resilience testing with controlled failures

### Monitoring Integration

- **Real-time Metrics**: Live performance monitoring
- **Alerting**: Automated alerts for test failures
- **Trend Analysis**: Long-term quality trend analysis
- **Regression Detection**: Automatic regression identification
