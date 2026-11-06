# Despliegue en Azure Container Apps (Azure for Students)

Decisión y datos en producción: [ADR-020](09-decisiones.md#adr-020--despliegue-en-azure-container-apps-con-contenedor-docker).
Todo se hace desde **Azure Cloud Shell** (portal.azure.com → botón `>_` arriba, modo **Bash**), que ya trae `az` y `git`.
No hace falta instalar nada en el computador. La cuenta Azure for Students da **100 USD de crédito sin tarjeta**.

| Qué | Valor |
|---|---|
| Grupo de recursos | `rg-g9` |
| App | `asistente-productores-cacao` (Container Apps; el entorno lo crea `az containerapp up`) |
| URL pública | https://asistente-productores-cacao.delightfulpond-e73b0c99.eastus.azurecontainerapps.io/ |
| Imagen | [Dockerfile](../Dockerfile) (`python:3.12-slim`, usuario sin privilegios, puerto `${PORT}` = 8080) |
| Recursos | 0,5 vCPU · 1 GiB · réplicas mín. 0 · máx. 1 |
| Secretos (de la app) | `gemini-key` → `GEMINI_API_KEY` · `groq-key` → `GROQ_API_KEY` |
| Variables (no secretas) | `LLM_PRINCIPAL=gemini` · `LLM_RESPALDO=groq` · `LLM_TIMEOUT_S=8` · `GEMINI_MODEL` · `GROQ_MODEL` · `APP_VERSION` · `PORT=8080` |
| Salud | `GET /health` → `{"estado": "ok", …}` sin llamar al modelo |

> **Gemini principal, Groq respaldo.** Gemini además calcula los embeddings de cada pregunta (búsqueda híbrida).
> `LLM_TIMEOUT_S=8` hace que, si Gemini se cuelga o responde «high demand», la app pase a Groq en segundos y no en 30 s
> (medición del 05/11 en [07-evaluacion.md](07-evaluacion.md) §2.1). Groq gratis admite ~200 000 tokens al día.

> **Costo:** Container Apps con réplicas mín. 0 entra en la capa gratuita mensual. Lo que sí consume crédito es el
> registro de imágenes (Azure Container Registry, plan Basic ≈ 5 USD/mes de los 100 USD). Al terminar el semestre,
> borrar todo con `az group delete --name rg-g9`.

## 0. Probar la imagen en local (opcional, con Docker Desktop)

```powershell
docker build -t g9-cacao .
docker run --rm -p 8080:8080 --env-file .env -e LLM_TIMEOUT_S=8 g9-cacao
# abrir http://localhost:8080/health y http://localhost:8080
```

## 1. Abrir Cloud Shell y preparar la suscripción (una vez)

1. Entrar a **portal.azure.com** con el correo de Azure for Students.
2. Botón **`>_`** (arriba, junto al buscador) → **Bash**. Si pregunta por almacenamiento, elegir
   **«No storage account required»** (sesión temporal; basta para esto).
3. Pegar:

```bash
az account show --query "{suscripcion:name, estado:state}" -o table   # debe decir Azure for Students / Enabled
az extension add --name containerapp --upgrade
az provider register --namespace Microsoft.App --wait
az provider register --namespace Microsoft.OperationalInsights --wait
az provider register --namespace Microsoft.ContainerRegistry --wait
az group create --name rg-g9 --location eastus
```

Si `az group create` (o el paso 3) da un error de **política / región no permitida** (`RequestDisallowedByAzure`),
la cuenta de estudiante solo admite algunas regiones y el mensaje las lista. Usar una de ellas (por ejemplo `eastus2`,
`westus2` o `brazilsouth`) en lugar de `eastus` en todos los comandos.

**Alerta de presupuesto:** Portal › **Cost Management** › **Budgets** › *Add* → 10 USD sobre la suscripción, alertas al
50, 90 y 100 %.

## 2. Bajar el código

```bash
git clone -b NOMBRE_DE_LA_RAMA https://github.com/AokingDev/Asistente_Productores_Cacao.git
cd Asistente_Productores_Cacao
```

Si el repositorio es privado, `git clone` pide usuario y contraseña: la contraseña es un *token* de GitHub
(Settings › Developer settings › Personal access tokens). Cuando el Dockerfile esté en `main`, usar `-b main`.

## 3. Construir y crear la app (5 a 10 minutos)

`containerapp up` sube el código, construye la imagen **en la nube** con el Dockerfile (crea un registro ACR en
`rg-g9`), crea el entorno y la app con una URL pública https.

```bash
az containerapp up --name asistente-productores-cacao --resource-group rg-g9 --location eastus \
  --source . --ingress external --target-port 8080 \
  --env-vars LLM_PRINCIPAL=gemini LLM_RESPALDO=groq LLM_TIMEOUT_S=8 \
             GEMINI_MODEL=gemini-3.5-flash-lite GROQ_MODEL=openai/gpt-oss-20b APP_VERSION=0.3.0 PORT=8080
```

En este punto la app arranca **sin claves**: `/health` ya responde, y el chat contesta «El asistente aún no está
configurado» hasta el paso 4.

> **Si falla con `TasksOperationsNotAllowed` o «ACR Tasks … not permitted»** (pasa en Azure for Students): la
> suscripción no permite construir en el registro. Seguir el **plan B** al final, que reemplaza los pasos 3 y 4.

## 4. Las claves como secretos de la app

`read -s` no muestra la clave en pantalla ni la deja en el historial. Pegar la clave y Enter.

```bash
read -s GEMINI    # clave de Gemini + Enter
read -s GROQ      # clave de Groq + Enter
az containerapp secret set --name asistente-productores-cacao --resource-group rg-g9 \
  --secrets gemini-key="$GEMINI" groq-key="$GROQ"
unset GEMINI GROQ

az containerapp update --name asistente-productores-cacao --resource-group rg-g9 \
  --set-env-vars GEMINI_API_KEY=secretref:gemini-key GROQ_API_KEY=secretref:groq-key \
  --cpu 0.5 --memory 1.0Gi --min-replicas 0 --max-replicas 1
```

`secretref:` hace que la variable tome el valor del secreto: la clave no aparece en la configuración visible de la app.
Para rotar una clave: repetir `secret set` con la nueva y luego `az containerapp update` (crea una revisión nueva).

Por qué estas opciones: **0,5 vCPU / 1 GiB** (Container Apps exige memoria = 2 × CPU; la app no carga modelos locales);
**réplicas mín. 0** se apaga sin tráfico (no gasta, pero hay arranque en frío); **máx. 1** limita el gasto y evita que las
propuestas de registro pendientes (en memoria) se repartan entre copias.

## 5. Probar

```bash
URL=https://$(az containerapp show --name asistente-productores-cacao --resource-group rg-g9 \
      --query properties.configuration.ingress.fqdn -o tsv)
echo $URL
curl -s $URL/health        # {"estado":"ok", … "llm":{"principal":"gemini","respaldo":"groq"} …}
curl -sN $URL/chat -H 'Content-Type: application/json' \
  -d '{"mensaje":"¿Cómo controlo la moniliasis?"}' | tail -1
```

Abrir `$URL` en el navegador o el celular: es la interfaz del chat. Registros si algo falla:

```bash
az containerapp logs show --name asistente-productores-cacao --resource-group rg-g9 --tail 50
az containerapp logs show --name asistente-productores-cacao --resource-group rg-g9 --type system --tail 50   # errores de arranque
```

**Antes de una demo:** abrir `URL/health` uno o dos minutos antes para despertar la app (arranque en frío).

## 6. Despliegue automático desde GitHub (CI/CD)

`.github/workflows/ci-cd.yml` corre **gitleaks + pytest + build de la imagen** en cada push y pull request. El job
`desplegar` corre solo en push a `main`, solo si `pruebas` pasó (`needs: pruebas`), y solo cuando el equipo lo activa:

1. Credencial para GitHub limitada al grupo de recursos (en Cloud Shell):

   ```bash
   SUB=$(az account show --query id -o tsv)
   az ad sp create-for-rbac --name gh-g9-cacao --role contributor \
     --scopes /subscriptions/$SUB/resourceGroups/rg-g9 --json-auth
   az acr list --resource-group rg-g9 --query "[0].name" -o tsv    # nombre del registro
   ```

2. En GitHub › Settings › Secrets and variables › Actions:
   - **Secrets** → `AZURE_CREDENTIALS` = el JSON completo que imprimió `create-for-rbac`.
   - **Variables** → `AZURE_ACR` = el nombre del registro · `DESPLEGAR_AZURE` = `true`.

Si `create-for-rbac` responde que no tiene permisos (el directorio de la universidad puede bloquear el registro de
aplicaciones), el pipeline se queda en el nivel mínimo (solo prueba) y el despliegue se repite a mano con el paso 7.

El workflow no pasa claves ni variables de los modelos: la app conserva sus secretos y variables entre revisiones.

## 7. Actualizar a mano después de un cambio

```bash
cd Asistente_Productores_Cacao && git pull
az containerapp up --name asistente-productores-cacao --resource-group rg-g9 --source .
```

Para cambiar de proveedor principal sin reconstruir:
`az containerapp update --name asistente-productores-cacao --resource-group rg-g9 --set-env-vars LLM_PRINCIPAL=groq LLM_RESPALDO=gemini`.

## Plan B · si la nube no puede construir la imagen (nuestro caso)

En Azure for Students, el paso 3 falla con `TasksOperationsNotAllowed`: la suscripción no permite **ACR Tasks**. Para
entonces `containerapp up` ya creó el entorno (`g9-cacao-env`) y el registro (en nuestro caso `cab7637514f2acr`). La
imagen se construye en el computador con Docker Desktop y se sube a ese registro; no hace falta la CLI de Azure en Windows.

**B1 · Cloud Shell:** habilitar el usuario del registro y ver su contraseña (no se guarda en ningún archivo).

```bash
ACR=$(az acr list --resource-group rg-g9 --query "[0].name" -o tsv); echo $ACR
az acr update --name $ACR --admin-enabled true
az acr credential show --name $ACR --query "passwords[0].value" -o tsv   # copiar
az containerapp env list --resource-group rg-g9 --query "[].name" -o tsv  # debe mostrar g9-cacao-env
```

**B2 · PowerShell en el computador** (carpeta del proyecto, Docker Desktop abierto):

```powershell
docker build -t cab7637514f2acr.azurecr.io/g9-cacao:1 .
docker login cab7637514f2acr.azurecr.io -u cab7637514f2acr    # pegar la contraseña de B1 (no se ve)
docker push cab7637514f2acr.azurecr.io/g9-cacao:1
docker logout cab7637514f2acr.azurecr.io
```

**B3 · Cloud Shell:** crear la app con la imagen, las variables y las claves en un solo paso (reemplaza los pasos 3 y 4).

```bash
read -s ACRPASS   # contraseña del registro (B1) + Enter
read -s GEMINI    # clave de Gemini + Enter
read -s GROQ      # clave de Groq + Enter
az containerapp create --name asistente-productores-cacao --resource-group rg-g9 --environment g9-cacao-env \
  --image $ACR.azurecr.io/g9-cacao:1 \
  --registry-server $ACR.azurecr.io --registry-username $ACR --registry-password "$ACRPASS" \
  --ingress external --target-port 8080 \
  --cpu 0.5 --memory 1.0Gi --min-replicas 0 --max-replicas 1 \
  --secrets gemini-key="$GEMINI" groq-key="$GROQ" \
  --env-vars LLM_PRINCIPAL=gemini LLM_RESPALDO=groq LLM_TIMEOUT_S=8 \
             GEMINI_MODEL=gemini-3.5-flash-lite GROQ_MODEL=openai/gpt-oss-20b APP_VERSION=0.3.0 PORT=8080 \
             GEMINI_API_KEY=secretref:gemini-key GROQ_API_KEY=secretref:groq-key
unset ACRPASS GEMINI GROQ
```

Luego seguir con el paso 5 (probar).

**Actualizar después de un cambio** (en lugar del paso 7): repetir B2 con una etiqueta nueva (`:2`, `:3`…) y en Cloud Shell
`az containerapp update --name asistente-productores-cacao --resource-group rg-g9 --image $ACR.azurecr.io/g9-cacao:2`. El pipeline de
GitHub (paso 6) construye la imagen en su propia máquina y la sube al registro, así que no depende de ACR Tasks.

## Lo que se pierde al reiniciar

Ver la tabla «Datos en producción» del ADR-020: las consultas registradas (`data/consultas/consultas.jsonl`) y
`logs/llm.jsonl` viven en el disco temporal del contenedor. Los eventos del log también salen por la consola y quedan en
**Log Analytics** (`az containerapp logs show`).
