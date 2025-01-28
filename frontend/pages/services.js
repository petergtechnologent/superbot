// File: frontend/pages/services.js
import { useQuery, useMutation } from "react-query";
import { getRunningServices, stopService } from "../utils/api";
import {
  Box,
  Heading,
  Text,
  Button,
  Flex,
  Spinner,
  useToast,
} from "@chakra-ui/react";
import { useState } from "react";

export default function Services() {
  const toast = useToast();
  const [selectedDeployment, setSelectedDeployment] = useState(null);

  // 1) Fetch running services
  const { data, refetch, isLoading } = useQuery(
    "runningServices",
    getRunningServices
  );

  // 2) Stop service mutation
  const { mutate: doStop } = useMutation(stopService, {
    onSuccess: (res) => {
      toast({
        title: "Service Stopped",
        description: `Deployment ${res.deployment_id} is now stopped.`,
        status: "success",
        duration: 3000,
        isClosable: true,
      });
      refetch(); // refresh list
    },
    onError: (err) => {
      toast({
        title: "Error stopping service",
        description: err.message,
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    },
  });

  const handleStop = (deploymentId) => {
    setSelectedDeployment(deploymentId);
    doStop({ deployment_id: deploymentId });
  };

  if (isLoading) {
    return (
      <Flex align="center" justify="center" mt={8}>
        <Spinner />
        <Text ml={2}>Loading Services...</Text>
      </Flex>
    );
  }

  return (
    <Box>
      <Heading>Running Flex Services</Heading>
      {(!data || data.length === 0) && (
        <Text mt={4}>No running services found.</Text>
      )}
      {data &&
        data.map((dep) => (
          <Box key={dep._id} p={4} my={2} bg="gray.700">
            <Text>Deployment ID: {dep._id}</Text>
            <Text>
              App Name:{" "}
              <Text as="span" fontWeight="bold" color="orange.300">
                {dep.app_name}
              </Text>
            </Text>
            <Text>Status: {dep.status}</Text>
            <Text>Port: {dep.port_number}</Text>
            <Text>Container ID: {dep.container_id}</Text>
            <Button
              mt={2}
              colorScheme="red"
              onClick={() => handleStop(dep._id)}
              isLoading={selectedDeployment === dep._id}
            >
              Stop
            </Button>
          </Box>
        ))}
    </Box>
  );
}
