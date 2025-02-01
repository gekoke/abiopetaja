{ self, ... }:
{
  perSystem =
    {
      config,
      pkgs,
      system,
      ...
    }:
    {
      devShells = {
        default = pkgs.mkShellNoCC {
          inputsFrom = [ self.packages.${system}.abiopetaja-dev ];

          packages = [
            pkgs.awscli2
            pkgs.deploy-rs.deploy-rs
            pkgs.djhtml
            pkgs.djlint
            pkgs.opentofu
            pkgs.poetry
            pkgs.poppler_utils
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

        cd = pkgs.mkShellNoCC { packages = [ pkgs.deploy-rs.deploy-rs ]; };
      };
    };
}
