{ self, ... }:
{
  perSystem = { config, pkgs, system, ... }: {
    devShells = {
      default = pkgs.mkShellNoCC {
        inputsFrom = [ self.packages.${system}.default ];

        packages = [
          pkgs.deploy-rs
          pkgs.opentofu
          pkgs.poetry
          pkgs.pyright
          pkgs.ruff
          pkgs.texliveBasic
        ];

        shellHook = ''
          ${config.pre-commit.installationScript}
          export PYTHONDONTWRITEBYTECODE=1
          export DJANGO_SETTINGS_MODULE="abiopetaja.settings_dev"
        '';
      };
    };
  };
}
