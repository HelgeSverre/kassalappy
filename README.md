# kassalappy: Python Client for Kassal.app API

kassalappy is a Python client library designed to interact with the Kassalapp API, providing a convenient way to access its features programmatically. It also includes a command-line interface (CLI) for easy interaction with the API from the terminal.

## Features

- Asynchronous design using `aiohttp` for non-blocking API calls.
- Pydantic models for data validation and serialization.
- Custom exceptions for handling API errors.
- CLI with commands for health checks, managing shopping lists, searching products, and more.
- Tabulated output for CLI commands for better readability.

## Installation

To install kassalappy, you can use pip:

```bash
pip install kassalappy
```

## Usage

### As a Library

To use kassalappy as a library, you need to create an instance of the `Kassalapp` class with your API access token:

```python
from kassalappy import Kassalapp

client = Kassalapp(access_token='your_access_token_here')
```

You can then use the client to perform various operations, such as:

```python
# Check API health
health_status = await client.healthy()

# Get shopping lists
shopping_lists = await client.get_shopping_lists()

# Search for products
products = await client.product_search(search='milk')
```

### As a CLI

kassalappy also provides a CLI for interacting with the Kassalapp API. Here are some examples of CLI commands:

```bash
# Check API health
kassalappy health --token your_access_token_here

# Get shopping lists
kassalappy shopping-lists --token your_access_token_here

# Search for products
kassalappy product "milk" --token your_access_token_here
```

## Documentation

For more detailed information about the API endpoints and data models, refer to the official Kassalapp API documentation: [Kassal.app API Docs](https://kassal.app/docs/api)

## Contributing

Contributions to kassalappy are welcome! Please follow the standard GitHub flow for submitting pull requests.

## License

kassalappy is released under the MIT License. See the LICENSE file for more details.

---

This README provides a general overview of the kassalappy client. For specific details on the API methods and CLI commands, please refer to the source code and the official API documentation.
