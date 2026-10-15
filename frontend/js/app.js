// Ponto de entrada da página.
import { enviarCodigo } from "./api.js";
import { EXEMPLOS } from "./exemplos.js";
import { iniciarInterface } from "./interface.js";

iniciarInterface(document.body, { enviar: enviarCodigo, exemplos: EXEMPLOS });
