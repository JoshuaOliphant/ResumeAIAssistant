{pkgs}: {
  deps = [
    pkgs.jq
    pkgs.libxcrypt
    pkgs.postgresql
    pkgs.openssl
  ];
}
