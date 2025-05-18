# Abiõpetaja

This project is a [Django](https://www.djangoproject.com/) web application. It uses the [SymPy symbolic math library](https://www.sympy.org) to generate math problems.

## Project Structure

The primary software components of note are as follows:

- [`./app`](./app/) - contains the business logic and the majority of the [MVC](https://en.wikipedia.org/wiki/Model%E2%80%93view%E2%80%93controller) code
- [`./app/tests/`](./app/tests/) - contains the integration tests for the application
- [`./app/math.py`](./app/math.py) - contains the logic for generating math problems
- [`./common/`](./common/) - contains some [templates](./common/templates/) and [Django template filter functions](./common/templatetags/). In practice, these might as well reside in the `app` project (see also on [Django filter function documentation](https://docs.djangoproject.com/en/5.1/ref/templates/language/#filters))
- [`./authentication/`](./authentication/) - contains [`django-allauth`](https://docs.allauth.org/en/latest/) template overrides for custom authentication flow views. See also: [`django-allauth` docs](https://docs.allauth.org/en/latest/index.html), [`django-allauth` docs section on templates](https://docs.allauth.org/en/latest/common/templates.html#templates)

## Dependencies

The only dependency for building the project and development is [Nix](https://nixos.org/).

It is recommended to install Nix using [the Determinate Nix Installer](https://zero-to-nix.com/concepts/nix-installer/#using), as it is generally more polished and provides more sensible defaults than the official installer. 

Nix only supports Unix platforms, but can be used on Windows through [WSL](https://learn.microsoft.com/en-us/windows/wsl/).

## Development

To develop, run:

```sh
nix develop
```

This will:

- Install all the dependencies at the correct versions
- Install all the development tooling (formatters, linters)
- Set up Git pre-commit hooks

To run the application:

```
python manage.py runserver
```

> [!TIP]
> You can use [`direnv`](https://direnv.net/) to automatically load this shell when entering the directory, and to reload it when its definition changes:
> ```sh
> nix profile install nixpkgs#direnv
> direnv allow
> ```

### Git Hooks

The project has a number `pre-commit` [Git Hooks](https://git-scm.com/book/ms/v2/Customizing-Git-Git-Hooks) to ensure that all committed changes pass [certain checks](./flake/checks.nix). These are run automatically before Git commits any changes.

The checks in include:

- `gitleak` - to check for accidental commits of secrets
- `ruff` - to lint Python files
- `ruff-format` - to format Python files
- `djhtml` - to format Django Template (`.djhtml`) files
- `djlint` - to lint Django Template (`.djhtml`) files
- `makemessages` - to ensure that any translations referenced in the source code have a corresponding entry in the translation source files
- `makemigrations` - to ensure that all changes to [migration files](./app/migrations/) are generated from [the model](./app/models.py)

### Tests

#### Integration Tests

To run the integration tests for the Django application:

```sh
pytest -n auto # `-n auto` is not strictly necessary, but parallelizes the tests based on available CPU count
```

#### Full Checks

To run the full suite of checks:

```sh
nix flake check
```

This will run:

- all [`pre-commit` hooks](#git-hooks)
- [the virtualized end-to-end NixOS tests](./flake/tests/default.nix)
- [the checks when building the package](./flake/packages.nix), which includes [the integration tests](./app/tests/) and static analysis with Pyright

The end-to-end tests are just a smoke test to ensure that the [machine configuration](./flake/nixos-configurations/default.nix) correctly sets up a service that can be communicated with by a client.

The end-to-end tests will take a long time to run, especially the first time before the cache for all the dependencies is populated - so there is little reason to run them in development.

> [!TIP]
> `nix flake check` [is also run in CI](./.github/workflows/ci.yaml) and [before any deployments](./.github/workflows/cd.yaml).

## Deployment

### Infrastructure

The service is intended to run on a single EC2 instance. It uses [SQLite](https://www.sqlite.org/) as its database system, which stores the data on the file system.

Inspect the [`infra/main.tf` file](./infra/main.tf) for the specific infrastructure that is provisioned.

### Quickstart

To deploy the application from a clean state:

- Generate a root user access key on AWS and store it locally in `~/.aws/credentials` - see [the AWS CLI docs](https://docs.aws.amazon.com/cli/v1/userguide/cli-configure-files.html#cli-configure-files-where) for more
- Generate a [public-private key pair](https://en.wikipedia.org/wiki/Public-key_cryptography) - using `ssh-keygen`, for example
- Replace the public key fingerprint in `./infra/main.tf` with your public key's fingerprint - this will be used to allow SSH connections to the machine for deployments
- In GitHub, [set a repository secret](https://github.com/gekoke/abiopetaja/settings/secrets/actions) with the name `SSH_PRIVATE_KEY` to your private key string. This is used in the [continuous deployment definition](./.github/workflows/cd.yaml) to deploy the configuration to the instance
- Provision the infrastructure with [OpenTofu](https://opentofu.org/):

```sh
cd infra
tofu plan
tofu apply
```

This generates a [text file containing the public IPv4 address of the instance](./infra/public_ip). Check this into version control, as it is used to deploy the machine configuration by [the deployment configuration](./flake/deploys.nix).


> [!NOTE]
> From this point onwards, any commits on the `main` branch will be automatically deployed to the live production instance.

> [!TIP]
> All checks run before anything is deployed from the `main` branch. If switching to the new configuration fails, the deployment rolls back to the previously working one.

### Teardown

> [!CAUTION]
> This will destroy the EC2 instance and therefore the SQLite database that resides on the filesystem!

To remove the provisioned infrastructure:

```sh
cd infra
tofu destroy
```


### Muutused mida veel vaja teha

-   Kõik probleemid JSON file'i 
-   Keelte vahetus 
-   AI prompti parandada (Liiga lihtsad ja mitte teemakohased ülesanded osad vastused valed. Step by step kaudu paljud õiged.) 
-   Lisada kastid ülesande lahendamiseks 
-   Kustutada ära mittevajalik stuff 

