
import { GoogleGenAI, Type } from "@google/genai";
import { CATEGORIES, MOCK_VIDEOS } from "./constants";

const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });

export const getSmartRecommendations = async (userPrompt: string) => {
  try {
    const videoTitles = MOCK_VIDEOS.map(v => v.title).join(", ");
    const categories = CATEGORIES.join(", ");

    const response = await ai.models.generateContent({
      model: "gemini-3-flash-preview",
      contents: `Usuário busca: "${userPrompt}". 
      Temos as categorias: [${categories}] e os vídeos: [${videoTitles}].
      
      Atue como um curador premium. 
      1. Identifique a categoria mais próxima do pedido.
      2. Sugira um vídeo específico da lista se houver correspondência.
      3. Responda em Português de forma curta e provocante.
      
      Retorne no formato JSON:
      {
        "text": "Sua resposta provocante aqui",
        "suggestedCategory": "NomeDaCategoria",
        "highlightVideoTitle": "Título do Vídeo"
      }`,
      config: {
        temperature: 0.7,
        responseMimeType: "application/json"
      }
    });

    return JSON.parse(response.text);
  } catch (error) {
    console.error("Gemini Error:", error);
    return {
      text: "Não consegui processar seu desejo agora, mas que tal explorar nossos destaques?",
      suggestedCategory: "All"
    };
  }
};
