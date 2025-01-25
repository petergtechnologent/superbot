import { useState } from "react";
import { useRouter } from "next/router";
import { Box, Button, Input, FormControl, FormLabel, Text, Select } from "@chakra-ui/react";
import { useMutation } from "react-query";
import { createNewUser } from "../utils/api";

export default function Signup() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("admin"); // default admin
  const [password, setPassword] = useState("");
  const { mutate: doSignup, error } = useMutation(createNewUser, {
    onSuccess: () => {
      // Once user is created, perhaps go to login
      router.push("/login");
    },
  });

  const handleSubmit = () => {
    doSignup({ username, email, role, password });
  };

  return (
    <Box maxW="md" mx="auto" mt={10}>
      <FormControl mb={4}>
        <FormLabel>Username</FormLabel>
        <Input
          placeholder="Enter username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
      </FormControl>

      <FormControl mb={4}>
        <FormLabel>Email</FormLabel>
        <Input
          type="email"
          placeholder="Enter email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
      </FormControl>

      <FormControl mb={4}>
        <FormLabel>Role</FormLabel>
        <Select value={role} onChange={(e) => setRole(e.target.value)}>
          <option value="admin">Admin</option>
          <option value="user">User</option>
        </Select>
      </FormControl>

      <FormControl mb={4}>
        <FormLabel>Password</FormLabel>
        <Input
          type="password"
          placeholder="Enter password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </FormControl>

      {error && <Text color="red.400">Signup failed: {error.message}</Text>}

      <Button colorScheme="orange" onClick={handleSubmit}>
        Sign Up
      </Button>
    </Box>
  );
}
