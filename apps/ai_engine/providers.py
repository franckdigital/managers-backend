import re

from django.conf import settings


class BaseAIProvider:
    def chat(self, messages, context=''):
        raise NotImplementedError

    def summarize(self, text):
        raise NotImplementedError

    def generate_quiz(self, content, num_questions=5):
        raise NotImplementedError

    def translate(self, text, target_lang):
        raise NotImplementedError

    def transcribe(self, file_obj):
        """§Sous-titrage automatique — speech-to-text on a lesson's audio/video file.
        Returns plain transcript text (no timing cues)."""
        raise NotImplementedError


class DummyAIProvider(BaseAIProvider):
    """Zero-dependency heuristic provider — works without any external API key so the
    AI features are usable out of the box. Swap LMSPRO_AI_PROVIDER to 'openai' or
    'anthropic' (with the matching API key set) for real generative answers."""

    def chat(self, messages, context=''):
        last_user_message = next((m['content'] for m in reversed(messages) if m['role'] == 'user'), '')
        prefix = f"À propos de « {context} » : " if context else ''
        return (
            f"{prefix}Je n'ai pas encore de moteur IA connecté, mais voici ce que je peux déjà faire : "
            f"reformuler votre question — « {last_user_message.strip()} » — et vous orienter vers les chapitres "
            "concernés. Configurez LMSPRO_AI_PROVIDER pour activer des réponses génératives complètes."
        )

    def summarize(self, text):
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        summary = ' '.join(sentences[:3])
        return summary or text[:280]

    def generate_quiz(self, content, num_questions=5):
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', content.strip()) if len(s.strip()) > 20]
        questions = []
        for sentence in sentences[:num_questions]:
            questions.append({
                'text': f'Vrai ou faux : « {sentence} »',
                'question_type': 'true_false',
                'choices': [{'text': 'Vrai', 'is_correct': True}, {'text': 'Faux', 'is_correct': False}],
            })
        return questions

    def translate(self, text, target_lang):
        return text

    def transcribe(self, file_obj):
        return (
            "Transcription automatique non disponible (aucun moteur de reconnaissance vocale connecté). "
            "Configurez LMSPRO_AI_PROVIDER=openai pour activer la transcription réelle."
        )


class OpenAIProvider(BaseAIProvider):
    def _client(self):
        from openai import OpenAI

        if not settings.OPENAI_API_KEY:
            raise RuntimeError('OPENAI_API_KEY non configurée')
        return OpenAI(api_key=settings.OPENAI_API_KEY)

    def chat(self, messages, context=''):
        client = self._client()
        system = {'role': 'system', 'content': f'Tu es un tuteur pédagogique pour la formation: {context}'}
        response = client.chat.completions.create(model='gpt-4o-mini', messages=[system, *messages])
        return response.choices[0].message.content

    def summarize(self, text):
        client = self._client()
        response = client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[{'role': 'user', 'content': f'Résume ce contenu pédagogique en 5 lignes max:\n\n{text}'}],
        )
        return response.choices[0].message.content

    def generate_quiz(self, content, num_questions=5):
        client = self._client()
        prompt = (
            f'Génère {num_questions} questions QCM (JSON: text, choices[{{text,is_correct}}]) à partir de ce contenu:\n\n{content}'
        )
        response = client.chat.completions.create(model='gpt-4o-mini', messages=[{'role': 'user', 'content': prompt}])
        import json

        return json.loads(response.choices[0].message.content)

    def translate(self, text, target_lang):
        client = self._client()
        response = client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[{'role': 'user', 'content': f'Traduis ce texte en {target_lang}:\n\n{text}'}],
        )
        return response.choices[0].message.content

    def transcribe(self, file_obj):
        client = self._client()
        response = client.audio.transcriptions.create(model='whisper-1', file=file_obj)
        return response.text


class AnthropicProvider(BaseAIProvider):
    def _client(self):
        import anthropic

        if not settings.ANTHROPIC_API_KEY:
            raise RuntimeError('ANTHROPIC_API_KEY non configurée')
        return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    def chat(self, messages, context=''):
        client = self._client()
        response = client.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=1024,
            system=f'Tu es un tuteur pédagogique pour la formation: {context}',
            messages=messages,
        )
        return response.content[0].text

    def summarize(self, text):
        return self.chat([{'role': 'user', 'content': f'Résume ce contenu pédagogique en 5 lignes max:\n\n{text}'}])

    def generate_quiz(self, content, num_questions=5):
        import json

        prompt = (
            f'Génère {num_questions} questions QCM en JSON (text, choices[{{text,is_correct}}]) uniquement, '
            f'sans texte autour, à partir de ce contenu:\n\n{content}'
        )
        raw = self.chat([{'role': 'user', 'content': prompt}])
        return json.loads(raw)

    def translate(self, text, target_lang):
        return self.chat([{'role': 'user', 'content': f'Traduis ce texte en {target_lang}:\n\n{text}'}])


_PROVIDERS = {'dummy': DummyAIProvider, 'openai': OpenAIProvider, 'anthropic': AnthropicProvider}


def get_ai_provider():
    provider_class = _PROVIDERS.get(settings.LMSPRO_AI_PROVIDER, DummyAIProvider)
    return provider_class()
