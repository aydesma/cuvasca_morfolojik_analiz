from flask import Flask, render_template, request
from morphology import analyze, AnalizHatasi, SAHISLAR, HALLER, SUTUNLAR
import os

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    analiz = None
    error = None
    root_word = ""

    # Seçimleri korumak için değişkenler
    selected_sahis = ""
    selected_plural = False
    selected_hal = "nominative"

    if request.method == 'POST':
        root = request.form.get('root', '').strip()
        root_word = root

        # Parametreleri al
        sahis_code = request.form.get('sahis', '')
        is_plural = request.form.get('plural') == 'on'
        hal = request.form.get('hal', 'nominative') or 'nominative'

        # Seçimleri koru
        selected_sahis = sahis_code
        selected_plural = is_plural
        selected_hal = hal

        if root:
            try:
                analiz = analyze(root, sahis_code or None, is_plural, hal)
            except AnalizHatasi as e:
                error = str(e)

    return render_template('index.html',
                         analiz=analiz,
                         error=error,
                         root=root_word,
                         selected_sahis=selected_sahis,
                         selected_plural=selected_plural,
                         selected_hal=selected_hal,
                         sahislar=SAHISLAR,
                         haller=HALLER,
                         sutunlar=SUTUNLAR)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)), debug=True)
