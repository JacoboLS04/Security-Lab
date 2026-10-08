# ISOs de instalación (medio de instalación manual)

Esta carpeta es **optativa**. No la necesita ni el código ni los scripts:
solo guarda las ISOs **tú las descargas y colocas aquí** (o donde prefieras) y
las usas para **crear manualmente** las VMs en VirtualBox.

El proyecto **nunca** descarga ISOs, no las monta automáticamente ni depende de
que existan.

## ISOs recomendadas

| Distribución | ISO recomendada | Arquitectura | Origen oficial |
|---|---|---|---|
| Debian 12 (bookworm) | **Debian 12 netinst** (`debian-12.x.y-amd64-netinst.iso`, ~650 MB) | amd64 | <https://cdimage.debian.org/debian-cd/current/amd64/iso-cd/> |
| Rocky Linux 9 | **Rocky 9 Minimal** (`Rocky-9.x-x86_64-minimal.iso`, ~2 GB) | x86_64 | <https://rockylinux.org/download> |

- **Debian netinst**: instalador mínimo que descarga el resto de paquetes
  durante la instalación (la VM tiene Internet por NAT). Basta para una
  instalación "servidor SSH".
- **Rocky Minimal**: sistema básico sin GUI; incluye SSHD. Menor superficie y
  menos recursos.

> Enlace vigente (el número menor cambia con cada release):
> · Debian: entra en `.../iso-cd/` y toma la `debian-12.*-amd64-netinst.iso`.
> · Rocky: `https://download.rockylinux.org/pub/rocky/9/isos/x86_64/` → `*-minimal.iso`.

## Dónde colocar la ISO

Si quieres conservarlas junto al proyecto, colócalas aquí:

```
infraestructura/iso/debian-12.iso
infraestructura/iso/rocky-9.iso
```

No necesitas renombrarlas: en VirtualBox **tú eliges el archivo** al configurar
la unidad óptica de la VM (Ver README principal → "Creación manual de máquinas
virtuales"). Nombrarlas igual solo facilita identificarlas.

## Verificar la integridad (SHA256)

Cada proyecto publica el archivo `SHA256SUMS` junto a las ISOs.

```bash
# descargar SHA256SUMS junto a la ISO y verificar
sha256sum -c SHA256SUMS --ignore-missing | grep -E 'OK|FAILED'

# o comparar directamente
sha256sum debian-12.iso      # -> comparar con el valor publicado en SHA256SUMS
```

En Windows PowerShell:

```powershell
Get-FileHash .\debian-12.iso -Algorithm SHA256
```

La suma garantiza que la descarga no está corrupta; la autenticidad la dan las
firmas oficiales (`SHA256SUMS.sign` de Debian, firmas Kozea/GPG de Rocky).

## ¿Por qué las ISOs no se suben a Git?

1. **Peso**: 650 MB a 2+ GB; Git no está hecho para binarios así.
2. **Origen**: son artefactos oficiales siempre descargables desde su fuente.
3. Por eso `../.gitignore` incluye `iso/*.iso`: solo se versiona este `README.md`.

## Flujo

```
ISO (tú la descargas) ──► VirtualBox (tú creas la VM) ──► VM instalada
```

La automatización del proyecto empieza **después**: `scripts/setup_debian.sh` /
`scripts/setup_rocky.sh` preparan el SO de una VM que **ya existe**.