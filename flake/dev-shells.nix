{ self, ... }:
{
  perSystem = { config, pkgs, system, ... }:
  let
    ####################################################################
    # 1.  Build ONE TeX Live bundle that includes TikZ
    ####################################################################
    tlWithTikZ = pkgs.texlive.combine {
      inherit (pkgs.texlive) scheme-small collection-pictures;  # pgf ⇒ tikz.sty
    };
  in
  {
    devShells = {
      default = pkgs.mkShellNoCC {
        inputsFrom = [ self.packages.${system}.abiopetaja-dev ];

        ################################################################
        # 2.  Put that bundle in buildInputs ❶
        ################################################################
        packages = [
          pkgs.deploy-rs.deploy-rs
          pkgs.opentofu
          pkgs.poetry
          pkgs.pyright
          pkgs.ruff
          tlWithTikZ                    # ← replaces pkgs.texliveBasic
          pkgs.poppler_utils
          pkgs.djhtml
          pkgs.djlint
        ];

        ################################################################
        # 3.  Make *its* bin/ come before /usr/bin in PATH ❷
        ################################################################
        shellHook = ''
          export PATH=${texliveWithTikZ}/bin:$PATH

          ${config.pre-commit.installationScript}
          export PYTHONDONTWRITEBYTECODE=1
          export DJANGO_SETTINGS_MODULE="abiopetaja.settings_dev"
        '';
      };

      cd = pkgs.mkShellNoCC { packages = [ pkgs.deploy-rs.deploy-rs ]; };
    };
  };
}
