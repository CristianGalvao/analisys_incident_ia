import os
import requests
import subprocess
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

GROQ_KEY = os.getenv('GROQ_KEY')
DISCORD_WEBHOOK = os.getenv('DISCORD_WEBHOOK')
LOKI_URL = os.getenv('LOKI_URL')

client = Groq(api_key=GROQ_KEY)

def search_log_loki(app_name):
    query = f'{{app="{app_name}"}}'
    params = {'query': query, 'limit': 50, 'direction': 'backward'}
    
    try:
        response = requests.get(LOKI_URL, params=params, timeout=5)
        if response.status_code == 200:
            results = response.json().get('data', {}).get('result', [])
            logs = "\n".join([line[1] for res in results for line in res.get('values', [])])
            return logs if logs else "Nenhum log encontrado no Loki."
        return f"Erro Loki: {response.status_code}"
    
    except Exception as e:
        return f"Falha no Loki: {e}"
        
def search_context_k8s(app_name):
    try:
        cmd = f"kubectl describe pod -l app={app_name} --tail=20"
        output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode('utf-8')
        return output[:1500]
    except subprocess.CalledProcessError as e:
        return f"Erro K8s ({e.returncode}): {e.output.decode('utf-8')[:300]}"
    except Exception as e:
        return f"Falha inesperada no K8s: {e}"
    
    
def analyze_incident(logs, summary, k8s_context):
    prompt = f"""
    VOCÊ É UM ENGENHEIRO SRE INVESTIGANDO UM INCIDENTE CRÍTICO.
    ALERTA: {summary}
    
    LOGS DA APLICAÇÃO:
    ---
    {logs}
    ---
    
    EVENTOS DE INFRAESTRUTURA (K8S):
    ---
    {k8s_context}
    ---
    
    TAREFAS:
    1. Identifique a CAUSA RAIZ técnica.
    2. Liste COMANDOS DE TERMINAL para validar a correção.
    3. Sugira uma MELHORIA DE INFRA (HPA, Limits, etc).
    """
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Você é um bot SRE que responde em Markdown técnico e direto."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Erro na análise da IA: {e}"


def send_discord(app_name, summary, diagnostico):
    corpo_mensagem = (
        f"**Alerta:** {summary}\n\n"
        f"**Análisando**\n"
        f"```markdown\n{diagnostico}\n```"
    )

    payload = {
        "embeds": [{
            "title": f"INCIDENTE DETECTADO: {app_name.upper()}",
            "description": corpo_mensagem,
            "color": 15158332,
            "footer": {"text": "SRE Engine | Groq Llama 3.3"}
        }]
    }
    
    try:
        r = requests.post(DISCORD_WEBHOOK, json=payload, timeout=10)
        if r.status_code in [200, 204]:
            print(f"Relatório enviado ao Discord: {app_name}")
        else:
            print(f"Erro Discord: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"Erro ao enviar para o Discord: {e}")