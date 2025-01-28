// File: frontend/pages/index.js
import { useState } from "react";
import { useMutation } from "react-query";
import Head from "next/head";
import {
  Box,
  Button,
  Textarea,
  Text,
  Input,
  Flex,
  Spinner,
  Checkbox,
  Heading,
} from "@chakra-ui/react";
import {
  transformFlexSpec,
  createConversation,
  generateCode,
  startDeployment,
} from "../utils/api";
import ActivityLog from "../components/ActivityLog";

export default function Home() {
  const [userIdea, setUserIdea] = useState("");
  const [flexPort, setFlexPort] = useState("9000");
  const [maxIterations, setMaxIterations] = useState(5);
  const [troubleMode, setTroubleMode] = useState(false);

  const [conversationId, setConversationId] = useState(null);
  const [deploymentId, setDeploymentId] = useState(null);
  const [codeData, setCodeData] = useState(null);

  const [isGenerating, setIsGenerating] = useState(false);
  const [isDeploying, setIsDeploying] = useState(false);

  // 1) Transform user input => Flex Spec
  const { mutate: doTransformSpec, isLoading: isTransformLoading } = useMutation(
    transformFlexSpec,
    {
      onSuccess: (spec) => {
        // 2) Create a conversation with that spec
        const specMessage = {
          role: "user",
          content: JSON.stringify(spec, null, 2),
        };
        doCreateConversation({ messages: [specMessage] });
      },
      onError: () => {
        setIsGenerating(false);
        alert("Error converting input into a Flex Spec!");
      },
    }
  );

  // 2) Create conversation => on success => generate code
  const { mutate: doCreateConversation } = useMutation(createConversation, {
    onSuccess: (res) => {
      setConversationId(res.conversation_id);
      doGenerateCode({
        conversation_id: res.conversation_id,
        prompt: "Generate code for the above Flex Spec.",
      });
    },
    onError: () => {
      setIsGenerating(false);
      alert("Error creating conversation!");
    },
  });

  // 3) Generate code
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

  // 4) Start deployment
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
    setIsGenerating(true);
    setCodeData(null);
    setDeploymentId(null);
    setConversationId(null);

    doTransformSpec({ userIdea });
  };

  const handleStartDeployment = () => {
    if (!conversationId) {
      alert("No conversation found. Generate code first.");
      return;
    }
    setIsDeploying(true);

    doStartDeploy({
      conversation_id: conversationId,
      app_name: "flex-fastapi-app",
      max_iterations: maxIterations,
      port_number: flexPort,
      trouble_mode: troubleMode,
    });
  };

  return (
    <Box p={4}>
      <Head>
        <title>Fast Service Generator</title>
      </Head>

      <Heading mb={4}>Fast Service Generator</Heading>

      <Text fontSize="md" mb={2}>
        Enter your microservice need:
      </Text>
      <Textarea
        value={userIdea}
        onChange={(e) => setUserIdea(e.target.value)}
        placeholder="e.g., 'A service on port 9090 with a GET /random endpoint for random numbers...'"
        mb={4}
      />

      <Flex align="center" mb={4}>
        <Text mr={2}>Port Number:</Text>
        <Input
          type="number"
          width="100px"
          value={flexPort}
          onChange={(e) => setFlexPort(e.target.value)}
        />
      </Flex>

      <Flex align="center" mb={4}>
        <Text mr={2}>Max Iterations:</Text>
        <Input
          type="number"
          width="100px"
          value={maxIterations}
          onChange={(e) => setMaxIterations(e.target.value)}
        />
      </Flex>

      {/* Trouble mode */}
      <Checkbox
        isChecked={troubleMode}
        onChange={(e) => setTroubleMode(e.target.checked)}
        mb={4}
      >
        Trouble Mode (Leave Container Running on Failure)
      </Checkbox>

      <Button
        onClick={handleSubmitPrompt}
        colorScheme="blue"
        isLoading={isTransformLoading || isGenerating}
        mb={6}
      >
        Generate Code
      </Button>

      {isGenerating && (
        <Flex mt={2} align="center">
          <Spinner mr={2} />
          <Text>Generating code, please wait...</Text>
        </Flex>
      )}

      {/* SERVICE SPEC TEXT */}
      {codeData && (
        <Box mt={4} p={4} bg="gray.700" color="white">
          <Text fontWeight="bold">Service Spec:</Text>
          <pre>{codeData}</pre>
        </Box>
      )}

      {/* START DEPLOYMENT BUTTON (moved out of the code box) */}
      {codeData && (
        <Button
          mt={2}
          onClick={handleStartDeployment}
          colorScheme="orange"
          isLoading={isDeploying}
        >
          Start Automated Deployment
        </Button>
      )}

      {isDeploying && (
        <Flex mt={2} align="center">
          <Spinner mr={2} />
          <Text>Deploying...</Text>
        </Flex>
      )}

      {deploymentId && (
        <Box mt={4}>
          <ActivityLog deploymentId={deploymentId} />
        </Box>
      )}
    </Box>
  );
}
