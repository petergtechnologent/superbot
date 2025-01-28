// File: frontend/components/ActivityLog.js
import { useEffect, useState } from "react";
import {
  Box,
  Text,
  useColorModeValue,
  Divider,
  chakra,
} from "@chakra-ui/react";
import { CheckCircleIcon } from "@chakra-ui/icons";

export default function ActivityLog({ deploymentId }) {
  const [logs, setLogs] = useState([]);
  const bgColor = useColorModeValue("gray.200", "gray.700");
  const textColor = useColorModeValue("black", "white");

  useEffect(() => {
    if (!deploymentId) return;

    const wsUrl = `ws://localhost:8000/deployments/logs/ws/${deploymentId}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log("WebSocket connected for deployment", deploymentId);
    };

    ws.onmessage = (event) => {
      setLogs((prev) => [...prev, event.data]);
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    ws.onclose = () => {
      console.log("WebSocket closed for deployment", deploymentId);
    };

    return () => {
      ws.close();
    };
  }, [deploymentId]);

  return (
    <Box mt={4} p={4} bg={bgColor} color={textColor} maxH="400px" overflowY="auto">
      <Text fontWeight="bold" mb={2}>
        Deployment Logs (ID: {deploymentId}):
      </Text>
      {logs.map((log, idx) => {
        const trimmed = log.trim();

        // Highlight iteration lines
        if (trimmed.includes("Iteration #")) {
          return (
            <Box key={idx} my={4}>
              <Divider borderColor="gray.500" mb={2} />
              <Text fontWeight="bold" color="teal.300">
                {log}
              </Text>
              <Divider borderColor="gray.500" mt={2} />
            </Box>
          );
        }

        // Show green check for SUCCESS lines
        if (trimmed.toUpperCase().includes("SUCCESS")) {
          return (
            <Box key={idx} my={2} display="flex" alignItems="center" color="green.400">
              <CheckCircleIcon mr={2} />
              <Text fontWeight="bold">{log}</Text>
            </Box>
          );
        }

        // Special highlight if line starts with "AI Plan" (existing logic example)
        if (trimmed.startsWith("AI Plan")) {
          return (
            <Text key={idx} fontSize="sm" fontWeight="bold" color="orange.300">
              {log}
            </Text>
          );
        }

        // Default log line
        return (
          <Text key={idx} fontSize="sm" my={1}>
            {log}
          </Text>
        );
      })}
    </Box>
  );
}
