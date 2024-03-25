{ self, pkgs, ... }:
{
  system.stateVersion = "24.05";

  networking.firewall.allowedTCPPorts = [
    80
    443
  ];

  services.nginx = {
    enable = true;
    resolver.ipv6 = false;
    recommendedProxySettings = true;
    recommendedTlsSettings = true;
    virtualHosts =
      let
        config = {
          forceSSL = true;
          enableACME = true;
          root = "/static";
          locations = {
            "/" = {
              tryFiles = "$uri @proxy";
              extraConfig = ''
                add_header X-Frame-Options SAMEORIGIN;
              '';
            };
            "@proxy" = {
              proxyPass = "http://127.0.0.1:8000";
              extraConfig = ''
                add_header X-Frame-Options SAMEORIGIN;
              '';
            };
          };
        };
      in
      {
        "xn--abipetaja-s7a.ee" = config;
        "www.xn--abipetaja-s7a.ee" = config;
      };
  };

  systemd.services.abiopetaja = {
    wantedBy = [ "multi-user.target" ];
    path = [ pkgs.texliveBasic ];
    serviceConfig = {
      ExecStart = "${self.packages.${pkgs.system}.default.dependencyEnv}/bin/gunicorn abiopetaja.wsgi:application";
    };
  };

  security.acme = {
    acceptTerms = true;
    defaults.email = "gregor@grigorjan.net";
  };
}
