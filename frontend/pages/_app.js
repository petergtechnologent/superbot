import { ChakraProvider } from "@chakra-ui/react";
import { QueryClient, QueryClientProvider } from "react-query";
import customTheme from "../theme";
import Layout from "../components/Layout";

const queryClient = new QueryClient();

function MyApp({ Component, pageProps }) {
  return (
    <QueryClientProvider client={queryClient}>
      <ChakraProvider theme={customTheme}>
        <Layout>
          <Component {...pageProps} />
        </Layout>
      </ChakraProvider>
    </QueryClientProvider>
  );
}

export default MyApp;
