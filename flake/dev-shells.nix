{ self, ... }:
{
  perSystem = { pkgs, system, ... }: {
    devShells = {
      default = pkgs.mkShellNoCC {
        inputsFrom = [ self.packages.${system}.default ];

        packages = [
          pkgs.poetry
          pkgs.ruff
          pkgs.texliveBasic
        ];

        shellHook = ''
          export PYTHONDONTWRITEBYTECODE=1
          export DJANGO_SETTINGS_MODULE="abiopetaja.settings_dev"
        '';
      };
    };
  };
}
