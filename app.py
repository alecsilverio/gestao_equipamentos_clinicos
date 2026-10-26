from flask import Flask, render_template


app = Flask(__name__)


@app.get("/")
def painel():
    """Exibe o painel visual inicial do sistema."""

    return render_template("painel.html")


if __name__ == "__main__":
    app.run(debug=True)