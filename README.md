# Bgtor Portainer Collection

`bgtor.portainer` Ansible Collection provides a comprehensive set of modules for interacting with the **Portainer API** to manage containerized environments programmatically.

<!--start requires_ansible-->
Requires Ansible >= 2.10
<!--end requires_ansible-->

## Description

The bgtor.portainer collection enables Portainer automation through Ansible, allowing you to:

- Manage **Stacks** (Docker Compose deployments) across multiple endpoints
- Configure **Secrets** and **Configs** for secure container orchestration
- Create and manage **Networks**, **Environments**, **Groups**, and **Tags**
- Query environment information and metadata
- Support for both **Docker Swarm** and **Docker Compose** stack types

## Modules

This collection includes 8 modules:

| Module | Purpose |
|--------|---------|
| `portainer_config` | Manage Docker configs (create, update, delete) |
| `portainer_secret` | Manage Docker secrets with secure handling |
| `portainer_network` | Create and manage Docker networks |
| `portainer_stack` | Deploy and manage Docker Compose and Swarm stacks |
| `portainer_environment` | Configure Portainer environments (Docker endpoints) |
| `portainer_environment_info` | Query information about environments |
| `portainer_group` | Organize environments into groups with tag support |
| `portainer_tag` | Create and manage resource tags |

All modules support **idempotent operations**, **check mode**, and **diff output** for safe automation.

## Requirements

This collection has no runtime dependencies beyond Ansible itself. The modules interact with Portainer API using only Ansible's built-in HTTP capabilities.

## Included content

Plugins and modules included in this collection:

- **8 Modules** for comprehensive Portainer resource management
- **Module utilities** with reusable CRUD operations, API client, and idempotency management
- **Documentation fragments** providing common parameter documentation

## Using this collection

### Installation

Install the collection from Ansible Galaxy:

```bash
ansible-galaxy collection install bgtor.portainer
```

Or include it in a `requirements.yml` file:

```yaml
collections:
  - name: bgtor.portainer
    version: ">=1.0.0"
```

Then install with:
```bash
ansible-galaxy collection install -r requirements.yml
```

### Upgrading

To upgrade to the latest version:

```bash
ansible-galaxy collection install bgtor.portainer --upgrade
```

Or install a specific version (e.g., to downgrade if needed):

```bash
ansible-galaxy collection install bgtor.portainer:==1.0.4
```

Browse all [available versions](https://galaxy.ansible.com/bgtor/portainer).

### Quick Start

Basic example - creating a Portainer stack:

```yaml
---
- name: Deploy application stack
  hosts: localhost
  gather_facts: false
  tasks:
    - name: Create stack from file
      bgtor.portainer.portainer_stack:
        portainer_url: https://portainer.example.com
        portainer_token: "{{ portainer_api_token }}"
        name: my-application
        stack_type: compose
        stack_source: file
        compose_file: /path/to/docker-compose.yml
        endpoint_id: 1
        state: present
```

### Documentation

For detailed module documentation and examples, see:
- [Collection Documentation on Ansible Galaxy](https://galaxy.ansible.com/ui/repo/published/bgtor/portainer/docs/)
- [Ansible Collections Guide](https://docs.ansible.com/ansible/latest/user_guide/collections_using.html)

Each module supports standard Ansible parameters:
- `portainer_url` - URL of your Portainer instance
- `portainer_token` - API access token
- `timeout` - Request timeout (default: 30s)
- `validate_certs` - SSL certificate validation (default: true)

## Examples

### Manage a Secret

```yaml
- name: Create application secret
  bgtor.portainer.portainer_secret:
    portainer_url: https://portainer.example.com
    portainer_token: "{{ portainer_api_token }}"
    name: db-password
    content: "{{ db_password }}"
    endpoint_id: 1
    state: present
```

### Manage a Network

```yaml
- name: Create overlay network
  bgtor.portainer.portainer_network:
    portainer_url: https://portainer.example.com
    portainer_token: "{{ portainer_api_token }}"
    name: backend
    driver: overlay
    endpoint_id: 1
    state: present
```

### Organize Resources with Tags and Groups

```yaml
- name: Create resource tag
  bgtor.portainer.portainer_tag:
    portainer_url: https://portainer.example.com
    portainer_token: "{{ portainer_api_token }}"
    name: production
    state: present

- name: Create environment group
  bgtor.portainer.portainer_group:
    portainer_url: https://portainer.example.com
    portainer_token: "{{ portainer_api_token }}"
    name: production-environments
    tags: ["production"]
    state: present
```

## Supported Ansible Versions

This collection supports Ansible >= 2.10 and has been tested on:
- Python 3.10, 3.11, 3.12
- Ansible 2.10+

## Release notes and Changelog

See the [CHANGELOG](./CHANGELOG.rst) for release notes and version history.

## Feature Highlights

### Idempotent Operations

All modules are idempotent, ensuring they can be safely run multiple times without unintended side effects:

```yaml
- name: Configure stack (safe to run repeatedly)
  bgtor.portainer.portainer_stack:
    # ... module parameters ...
    state: present
```

### Check Mode Support

Preview changes before applying them:

```bash
ansible-playbook playbook.yml --check
```

### Diff Output

See detailed diffs of what will change:

```bash
ansible-playbook playbook.yml --diff
```

### Error Handling

Comprehensive API error reporting with status codes and response details for debugging.

## Development and Testing

### Running Tests

Run all unit tests with ansible-test:

```bash
ansible-test units
```

Run tests for a specific module:

```bash
ansible-test units tests/unit/plugins/modules/test_portainer_config.py
```

Validate module syntax and imports:

```bash
ansible-test sanity --docker default # Needs docker installed
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass: `ansible-test units --docker default` (Needs docker installed)
5. Submit a pull request

## Support

- **Issue Tracker:** [GitHub Issues](https://github.com/bgtor/ansible-portainer/issues)
- **Community:** [Ansible Forum - Collections](https://forum.ansible.com/c/project/collection-development/27)

## More information

- [Ansible collection development forum](https://forum.ansible.com/c/project/collection-development/27)
- [Ansible User guide](https://docs.ansible.com/ansible/devel/user_guide/index.html)
- [Ansible Developer guide](https://docs.ansible.com/ansible/devel/dev_guide/index.html)
- [Ansible Collections Checklist](https://docs.ansible.com/ansible/devel/community/collection_contributors/collection_requirements.html)
- [Ansible Community code of conduct](https://docs.ansible.com/ansible/devel/community/code_of_conduct.html)
- [The Bullhorn (the Ansible Contributor newsletter)](https://docs.ansible.com/ansible/devel/community/communication.html#the-bullhorn)
- [News for Maintainers](https://forum.ansible.com/tag/news-for-maintainers)

## Licensing

GNU General Public License v3.0 or later.

See [LICENSE](https://www.gnu.org/licenses/gpl-3.0.txt) to see the full text.
