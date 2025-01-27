// File: frontend/pages/index.js
import { useState } from "react";
import { useMutation } from "react-query";
import {
  Box,
  Button,
  Textarea,
  Text,
  Input,
  Flex,
  Spinner,
  Select
} from "@chakra-ui/react";
import { createConversation, generateCode, startDeployment } from "../utils/api";
import ActivityLog from "../components/ActivityLog";

export default function Home() {
  const [prompt, setPrompt] = useState("");
  const [codeData, setCodeData] = useState(null);
  const [deploymentId, setDeploymentId] = useState(null);
  const [conversationId, setConversationId] = useState(null);

  // Max Iterations input
  const [maxIterations, setMaxIterations] = useState(5);

  // "script" vs "server"
  const [appType, setAppType] = useState("script");

  // Loading states
  const [isGenerating, setIsGenerating] = useState(false);
  const [isDeploying, setIsDeploying] = useState(false);

  // 1) Create conversation => on success => generate code
  const { mutate: doStartConversation } = useMutation(createConversation, {
    onSuccess: (res) => {
      console.log("Created conversation ID:", res.conversation_id);
      setConversationId(res.conversation_id);
      // then generate code
      doGenerateCode({ conversation_id: res.conversation_id, prompt });
    },
    onError: () => {
      setIsGenerating(false);
      alert("Error creating conversation!");
    },
  });

  // 2) Generate code
  const { mutate: doGenerateCode } = useMutation(generateCode, {
    onSuccess: (data) => {
      setCodeData(data.generated_code);
      setIsGenerating(false);
    },
    onError: () => {
      setIsGenerating(false);
      alert("Error generating code!");
    },
  });

  // 3) Start deployment
  const { mutate: doStartDeploy } = useMutation(startDeployment, {
    onSuccess: (res) => {
      setDeploymentId(res.deployment_id);
      setIsDeploying(false);
    },
    onError: () => {
      setIsDeploying(false);
      alert("Error starting deployment!");
    },
  });

  const handleSubmitPrompt = () => {
    setCodeData(null);
    setDeploymentId(null);
    setConversationId(null);
    setIsGenerating(true);

    doStartConversation({ messages: [{ role: "user", content: prompt }] });
  };

  const handleStartDeployment = () => {
    if (!conversationId) {
      alert("Generate code first (Conversation ID not found).");
      return;
    }
    console.log("Starting deployment with conversationId:", conversationId);
    setIsDeploying(true);
    doStartDeploy({
      conversation_id: conversationId,
      app_name: "my-python-app",
      max_iterations: maxIterations,
      app_type: appType,
    });
  };

  return (
    <Box p={4}>
      <Textarea
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder="Describe your app idea..."
      />
      <Button mt={2} onClick={handleSubmitPrompt} colorScheme="blue">
        Generate Code
      </Button>

      {isGenerating && (
        <Flex mt={2} align="center">
          <Spinner mr={2} />
          <Text>Generating code, please wait...</Text>
        </Flex>
      )}

      <Flex align="center" mt={4}>
        <Text mr={2}>Max Iterations:</Text>
        <Input
          type="number"
          width="100px"
          value={maxIterations}
          onChange={(e) => setMaxIterations(Number(e.target.value))}
        />
      </Flex>

      <Flex align="center" mt={4}>
        <Text mr={2}>App Type:</Text>
        <Select
          width="150px"
          value={appType}
          onChange={(e) => setAppType(e.target.value)}
        >
          <option value="script">Short Script</option>
          <option value="server">Long-Running Server</option>
        </Select>
      </Flex>

      {codeData && (
        <Box mt={4} p={4} bg="gray.700" color="white">
          <Text fontWeight="bold">Generated Code:</Text>
          <pre>{codeData}</pre>

          <Button mt={4} onClick={handleStartDeployment} colorScheme="orange">
            Start Automated Deployment
          </Button>
          {isDeploying && (
            <Flex mt={2} align="center">
              <Spinner mr={2} />
              <Text>Starting deployment...</Text>
            </Flex>
          )}
        </Box>
      )}

      {deploymentId && (
        <Box mt={4}>
          <ActivityLog deploymentId={deploymentId} />
        </Box>
      )}
    </Box>
  );
}
