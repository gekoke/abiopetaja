{
  inputs = {
    nixpkgs.url          = "github:nixos/nixpkgs/nixos-unstable";
    flake-parts.url      = "github:hercules-ci/flake-parts";
    pre-commit-hooks.url = "github:cachix/git-hooks.nix";
    deploy-rs.url        = "github:serokell/deploy-rs";
  };

  outputs = { nixpkgs, ... }:
  let
    system = "x86_64-linux";
    pkgs   = import nixpkgs { inherit system; };

    texliveWithTikZ = pkgs.texlive.combine {
      inherit (pkgs.texlive) scheme-small collection-pictures;  # pgf ⇒ tikz.sty
    };

    pythonEnv = pkgs.python3.withPackages (ps: with ps; [
      django django-allauth django-cleanup
      transformers torch accelerate
      pydantic openai psycopg2
      dj-database-url python-dotenv
      
    ]);
  in
  {
    devShells.${system}.default = pkgs.mkShell {

      buildInputs = [
        pythonEnv
        texliveWithTikZ           # ← now part of the env
        pkgs.postgresql # initdb, pg_ctl, psql
        pkgs.poetry # CLI for poetry lock/show
      ];

      shellHook = ''
        export PATH=${texliveWithTikZ}/bin:$PATH
        # Postgres data directory
        export PGDATA=$PWD/.pgdata
        mkdir -p "$PGDATA"

        # Initialize DB cluster if missing
        if [ ! -f "$PGDATA/PG_VERSION" ]; then
          echo ">>> Initializing Postgres cluster in $PGDATA"
          initdb --username=testuser --encoding=UTF8
        fi

        # Start Postgres with Unix socket inside PGDATA
        pg_ctl -o "-F -p 5432 -k '$PGDATA'" -w start >/dev/null 2>&1 || true

        # Ensure the Django database exists (via TCP)
        psql -U testuser -h localhost -p 5432 -lqt | cut -d \| -f1 | grep -qw math_tests \
          || createdb -U testuser -h localhost -p 5432 math_tests

        # Export DATABASE_URL for Django
        export DATABASE_URL="postgresql://testuser@localhost:5432/math_tests"
        echo ">>> Postgres ready, DATABASE_URL set"
      '';
    };
  };
}
