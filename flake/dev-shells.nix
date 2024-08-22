{ self, ... }:
{
  perSystem = { config, pkgs, system, inputs', ... }: {
    devShells = {
      default = pkgs.mkShellNoCC {
        inputsFrom = [ self.packages.${system}.abiopetaja-dev ];

        packages = [
          pkgs.deploy-rs
          pkgs.opentofu
          pkgs.poetry
          pkgs.pyright
          pkgs.ruff
          pkgs.texliveBasic
          pkgs.poppler_utils
          pkgs.djhtml
          pkgs.djlint
        ];

        shellHook = ''
          ${config.pre-commit.installationScript}
          export PYTHONDONTWRITEBYTECODE=1
          export DJANGO_SETTINGS_MODULE="abiopetaja.settings_dev"
        '';
      };

      cd = pkgs.mkShellNoCC {
        packages = [ pkgs.deploy-rs ];
      };
    };
  };
}
