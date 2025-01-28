// File: frontend/components/Layout.js
import { Box, Flex, Link, Heading, Button, Image } from "@chakra-ui/react";
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
      <Flex as="nav" bg="gray.900" p={4} justify="space-between" align="center">
        {/* NAVBAR LEFT: LOGO + TITLE */}
        <Flex align="center" gap={2}>
          <Image
            src="/my_company_logo.png"
            alt="Company Logo"
            boxSize="50px"
            width="auto"
            objectFit="contain"
          />
          <Heading size="xl">Text2Flex</Heading>
        </Flex>

        {/* NAVBAR RIGHT: LINKS */}
        <Flex gap={4} align="center">
          <Link as={NextLink} href="/">
            Home
          </Link>
          <Link as={NextLink} href="/history">
            History
          </Link>
          <Link as={NextLink} href="/services">
            Services
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
