# design-software-docs

Repositorio de documentación del proyecto **Horarios SENA**.

Este repositorio es la fuente de verdad documental del proyecto. Todo cambio debe pasar por rama, Pull Request y revisión; no se trabaja directamente sobre `dev`, `qa` ni `main`.

## Reglas rápidas

- Leer [CONTRIBUTING.md](./CONTRIBUTING.md) antes de agregar o mover documentos.
- Registrar cada archivo nuevo en el `README.md` de su sección.
- No publicar credenciales, tokens, llaves privadas, datos personales ni información sensible de infraestructura.
- Mantener fuente editable y exportación para cada diagrama.
- Usar `99-archive/` para preservar documentos deprecados; no eliminar historia sin acuerdo del equipo.

## Estructura

| Sección | Descripción | Estado |
|---------|-------------|--------|
| [00-governance](./00-governance/) | Reglas, convenciones y criterios del repo | 🟡 |
| [01-context](./01-context/) | Contexto institucional, alcance y glosario | 🔴 |
| [02-domain](./02-domain/) | Modelo de dominio y bounded contexts | 🔴 |
| [03-product](./03-product/) | Visión, roadmap y backlog de producto | 🔴 |
| [04-requirements](./04-requirements/) | Requisitos funcionales y no funcionales | 🔴 |
| [05-architecture](./05-architecture/) | Vistas arquitectónicas y ADRs | 🔴 |
| [06-data](./06-data/) | Modelos de datos y estrategia de migración | 🔴 |
| [07-api](./07-api/) | Guidelines, autenticación y contratos OpenAPI | 🔴 |
| [08-uml](./08-uml/) | Diagramas UML (fuentes y exportaciones) | 🔴 |
| [09-microservices](./09-microservices/) | Catálogo de servicios y plantilla | 🔴 |
| [10-devops](./10-devops/) | Setup local, CI/CD y entornos | 🔴 |
| [11-quality](./11-quality/) | Estrategia de testing y code review | 🔴 |
| [12-ux-ui](./12-ux-ui/) | Design system, navegación y wireframes | 🔴 |
| [13-operations](./13-operations/) | Observabilidad, incidentes y backups | 🔴 |
| [14-training](./14-training/) | Manuales de usuario, admin y onboarding | 🔴 |
| [15-project-control](./15-project-control/) | Backlog técnico, riesgos y dependencias | 🔴 |
| [99-archive](./99-archive/) | Decisiones y documentos deprecados | 🟡 |

## Estado de íconos
- 🔴 Pendiente — 🟡 En progreso — 🟢 Estable
- ⚫ Deprecado

## Documentos de gobierno

- [Guía de contribución](./CONTRIBUTING.md)
- [Reglas de documentación](./00-governance/documentation-rules.md)
- [Convenciones de Git](./00-governance/git-conventions.md)
- [Documentación de microservicios](./00-governance/microservices-documentation.md)
- [Seguridad documental](./00-governance/security-rules.md)
- [Definition of Ready](./00-governance/definition-of-ready.md)
- [Definition of Done](./00-governance/definition-of-done.md)
- [CHANGELOG](./CHANGELOG.md)
- [CODEOWNERS](./.github/CODEOWNERS)
