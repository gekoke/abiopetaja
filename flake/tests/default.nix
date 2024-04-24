{ self, pkgs, ... }:
let
  nodesDefinition = {
    node.specialArgs = { inherit (self.packages.${pkgs.system}) abiopetaja; };
    nodes = {
      server = import ./test-vm-server.nix { inherit self pkgs; };
      client = import ./test-vm-client.nix { inherit pkgs; };
    };
  };
  tests = [
    ({
      name = "smoke_test_server_responds_to_client";

      testScript = ''
        server.wait_for_unit("nginx.service")
        server.wait_for_unit("abiopetaja.service")
        client.wait_for_unit("network.target")

        client.wait_until_succeeds("curl -L http://server/ | grep -o \"Sign up\"", timeout=60)
      '';
    })
    ({
      name = "test_server_serves_static_resources";

      testScript = ''
        server.wait_for_unit("nginx.service")
        server.wait_for_unit("abiopetaja.service")
        client.wait_for_unit("network.target")

        client.wait_until_succeeds("wget http://server/static/app/example.pdf", timeout=60)
      '';
    })
  ];
in
builtins.listToAttrs (
  map
    (test: {
      name = test.name;
      value = pkgs.testers.runNixOSTest (test // nodesDefinition);
    })
    tests
)
