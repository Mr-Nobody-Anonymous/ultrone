{{/*
ULTRONE Helm Chart Helpers
*/}}

{{/*
Expand the name of the chart.
*/}}
{{- define "ultrone.name" -}}
{{- default .Chart.Name .Values.global.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "ultrone.fullname" -}}
{{- if .Values.global.fullnameOverride }}
{{- .Values.global.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.global.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "ultrone.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "ultrone.labels" -}}
helm.sh/chart: {{ include "ultrone.chart" . }}
{{ include "ultrone.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- range $key, $value := .Values.commonLabels }}
{{ $key }}: {{ $value | quote }}
{{- end }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "ultrone.selectorLabels" -}}
app.kubernetes.io/name: {{ include "ultrone.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "ultrone.serviceAccountName" -}}
{{- if .Values.serviceAccounts.create }}
{{- default (include "ultrone.fullname" .) .Values.serviceAccounts.name }}
{{- else }}
{{- default "default" .Values.serviceAccounts.name }}
{{- end }}
{{- end }}

{{/*
Create the name of the API component
*/}}
{{- define "ultrone.api.name" -}}
{{- if .Values.api.name }}
{{- .Values.api.name }}
{{- else }}
{{- printf "%s-api" (include "ultrone.fullname" .) }}
{{- end }}
{{- end }}

{{/*
Create the name of the Worker component
*/}}
{{- define "ultrone.worker.name" -}}
{{- if .Values.worker.name }}
{{- .Values.worker.name }}
{{- else }}
{{- printf "%s-worker" (include "ultrone.fullname" .) }}
{{- end }}
{{- end }}

{{/*
Create the name of the Frontend component
*/}}
{{- define "ultrone.frontend.name" -}}
{{- if .Values.frontend.name }}
{{- .Values.frontend.name }}
{{- else }}
{{- printf "%s-frontend" (include "ultrone.fullname" .) }}
{{- end }}
{{- end }}

{{/*
Create the name of the Redis component
*/}}
{{- define "ultrone.redis.name" -}}
{{- if .Values.redis.name }}
{{- .Values.redis.name }}
{{- else }}
{{- printf "%s-redis" (include "ultrone.fullname" .) }}
{{- end }}
{{- end }}

{{/*
Create the name of the Qdrant component
*/}}
{{- define "ultrone.qdrant.name" -}}
{{- if .Values.qdrant.name }}
{{- .Values.qdrant.name }}
{{- else }}
{{- printf "%s-qdrant" (include "ultrone.fullname" .) }}
{{- end }}
{{- end }}

{{/*
Create the name of the Postgres component
*/}}
{{- define "ultrone.postgres.name" -}}
{{- if .Values.postgres.name }}
{{- .Values.postgres.name }}
{{- else }}
{{- printf "%s-postgres" (include "ultrone.fullname" .) }}
{{- end }}
{{- end }}

{{/*
Create the name of the MediaMTX component
*/}}
{{- define "ultrone.mediamtx.name" -}}
{{- if .Values.mediamtx.name }}
{{- .Values.mediamtx.name }}
{{- else }}
{{- printf "%s-mediamtx" (include "ultrone.fullname" .) }}
{{- end }}
{{- end }}

{{/*
Create the name of the Grafana component
*/}}
{{- define "ultrone.grafana.name" -}}
{{- if .Values.grafana.name }}
{{- .Values.grafana.name }}
{{- else }}
{{- printf "%s-grafana" (include "ultrone.fullname" .) }}
{{- end }}
{{- end }}

{{/*
Create the name of the Prometheus component
*/}}
{{- define "ultrone.prometheus.name" -}}
{{- if .Values.prometheus.name }}
{{- .Values.prometheus.name }}
{{- else }}
{{- printf "%s-prometheus" (include "ultrone.fullname" .) }}
{{- end }}
{{- end }}

{{/*
Create the name of the Loki component
*/}}
{{- define "ultrone.loki.name" -}}
{{- if .Values.loki.name }}
{{- .Values.loki.name }}
{{- else }}
{{- printf "%s-loki" (include "ultrone.fullname" .) }}
{{- end }}
{{- end }}

{{/*
Render image name with optional registry
*/}}
{{- define "ultrone.image" -}}
{{- $registry := default .root.Values.global.imageRegistry .local.registry }}
{{- if $registry }}
{{- printf "%s/%s:%s" $registry .local.repository .local.tag }}
{{- else }}
{{- printf "%s:%s" .local.repository .local.tag }}
{{- end }}
{{- end }}

{{/*
Generate basic labels for sub-components
*/}}
{{- define "ultrone.componentLabels" -}}
app.kubernetes.io/name: {{ include "ultrone.name" . }}
app.kubernetes.io/component: {{ .component }}
app.kubernetes.io/instance: {{ .Release.Name }}
helm.sh/chart: {{ include "ultrone.chart" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Create the ingress host path rules
*/}}
{{- define "ultrone.ingressRules" -}}
{{- $fullName := include "ultrone.fullname" . -}}
{{- $servicePort := .servicePort -}}
{{- range $host := .hosts }}
- host: {{ $host.host | quote }}
  http:
    paths:
      {{- range $path := $host.paths }}
      - path: {{ $path.path }}
        pathType: {{ $path.pathType }}
        backend:
          service:
            name: {{ $fullName }}
            port:
              number: {{ $servicePort }}
      {{- end }}
{{- end }}
{{- end }}