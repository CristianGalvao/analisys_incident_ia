from flask import Flask, request
from functions import search_context_k8s,search_log_loki,send_discord, analyze_incident

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook_handler():
    data = request.json
    print(f"Webhook recebido do Grafana...")
    
    if not data or 'alerts' not in data:
        return "Invalid payload", 400

    for alert in data.get('alerts', []):
        if alert.get('status') == 'firing':
            labels = alert.get('labels', {})
            app_name = labels.get('app', 'default')
            summary = alert.get('annotations', {}).get('summary', 'Alerta detectado')
            
            print(f"Investigando: {app_name}")
            logs = search_log_loki(app_name)
            k8s_data = search_context_k8s(app_name)
            diagnostico = analyze_incident(logs, summary, k8s_data)
            
            send_discord(app_name, summary, diagnostico)
            
    return "OK", 200



if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)