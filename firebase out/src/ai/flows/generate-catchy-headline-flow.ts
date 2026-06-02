'use server';
/**
 * @fileOverview A Genkit flow for generating catchy, bold headlines from news article bodies.
 *
 * - generateCatchyHeadline - A function that handles the headline generation process.
 * - GenerateCatchyHeadlineInput - The input type for the generateCatchyHeadline function.
 * - GenerateCatchyHeadlineOutput - The return type for the generateCatchyHeadline function.
 */

import {ai} from '@/ai/genkit';
import {z} from 'genkit';

const GenerateCatchyHeadlineInputSchema = z.object({
  articleBody: z.string().describe('The full text body of the news article.'),
});
export type GenerateCatchyHeadlineInput = z.infer<typeof GenerateCatchyHeadlineInputSchema>;

const GenerateCatchyHeadlineOutputSchema = z.object({
  headline: z.string().describe('A catchy and bold headline for the news article.'),
});
export type GenerateCatchyHeadlineOutput = z.infer<typeof GenerateCatchyHeadlineOutputSchema>;

export async function generateCatchyHeadline(
  input: GenerateCatchyHeadlineInput
): Promise<GenerateCatchyHeadlineOutput> {
  return generateCatchyHeadlineFlow(input);
}

const generateCatchyHeadlinePrompt = ai.definePrompt({
  name: 'generateCatchyHeadlinePrompt',
  input: {schema: GenerateCatchyHeadlineInputSchema},
  output: {schema: GenerateCatchyHeadlineOutputSchema},
  prompt: `You are an expert news editor. Your task is to read the following article body and generate a single, catchy, and bold headline for it.

Make sure the headline is concise, attention-grabbing, and accurately reflects the main point of the article.

Article Body:
"""{{{articleBody}}}"""

Generated Headline: `,
});

const generateCatchyHeadlineFlow = ai.defineFlow(
  {
    name: 'generateCatchyHeadlineFlow',
    inputSchema: GenerateCatchyHeadlineInputSchema,
    outputSchema: GenerateCatchyHeadlineOutputSchema,
  },
  async input => {
    const {output} = await generateCatchyHeadlinePrompt(input);
    return output!;
  }
);
