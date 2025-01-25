import { extendTheme } from "@chakra-ui/react";

const colors = {
  brand: {
    navy: "#183252",
    accent1: "#f68112",
    accent2: "#f97405",
    secondary: "#749cac",
    light: "#f3f5f2",
  }
};

const config = {
  initialColorMode: "dark",
  useSystemColorMode: false,
};

const customTheme = extendTheme({ config, colors });

export default customTheme;
