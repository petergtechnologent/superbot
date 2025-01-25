import { Box, Flex, Link, Heading, Button } from "@chakra-ui/react";
import NextLink from "next/link";
import { useEffect, useState } from "react";

export default function Layout({ children }) {
  const [token, setToken] = useState(null);

  useEffect(() => {
    const storedToken = localStorage.getItem("access_token");
    if (storedToken) setToken(storedToken);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    setToken(null);
  };

  return (
    <Box minH="100vh" bg="gray.800" color="gray.100">
      <Flex as="nav" bg="gray.900" p={4} justify="space-between">
        <Heading size="md">AI App Generator</Heading>
        <Flex gap={4} align="center">
          <Link as={NextLink} href="/">
            Home
          </Link>
          <Link as={NextLink} href="/history">
            History
          </Link>

          {!token ? (
            <>
              <Link as={NextLink} href="/login">
                Login
              </Link>
              <Link as={NextLink} href="/signup">
                Sign Up
              </Link>
            </>
          ) : (
            <Button onClick={handleLogout} colorScheme="red" variant="outline" size="sm">
              Logout
            </Button>
          )}
        </Flex>
      </Flex>
      <Box p={6}>{children}</Box>
    </Box>
  );
}
