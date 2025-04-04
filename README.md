MomVisionAI
This repository contains the code for MomVision AI, an MVP designed to assist pregnant individuals in making informed dietary decisions. This application assists pregnant individuals in assessing food safety and nutritional value through image analysis. Users upload a picture, which is processed by a Flask backend on Google Cloud. The system identifies the food using the Vision API and then employs the Gemini API to provide a concise safety evaluation relevant to expectant mothers, considering local context. Major vitamins present in the identified food are also listed. For more comprehensive insights, Gemini generates general nutritional information and benefits during pregnancy. Audio summaries of the analysis are created in both English and Hindi using Google Cloud Text-to-Speech. The frontend displays the identified food, safety assessment, vitamin information, detailed text, and audio playback options. Firebase Storage facilitates temporary image uploads. This tool aims to empower informed dietary choices for maternal health.

Features
Identifies food from image.
Generates food safety information and health tips using Gemini API.
Provides voice output in English and Hindi using Text-to-Speech API.
