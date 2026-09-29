import type { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "app.mokli.personal",
  appName: "Mokli",
  webDir: "../web/dist",
  server: {
    url: process.env.MOKLI_GATEWAY_URL || "https://mokli.lork.cloud",
    androidScheme: "https",
    cleartext: true,
  },
};

export default config;
