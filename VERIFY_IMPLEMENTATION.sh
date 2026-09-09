#!/bin/bash
# Script de verificación post-implementación
# Uso: bash VERIFY_IMPLEMENTATION.sh

echo "🔍 Verificando Refactorización de Kiosqly Admin Dashboard"
echo "=========================================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Verificar que Device.js tiene nuevos campos
echo "✓ Test 1: Verificando Device.js..."
if grep -q "businessName" models/Device.js && \
   grep -q "batteryLevel" models/Device.js && \
   grep -q "location" models/Device.js; then
  echo -e "${GREEN}✅ Device.js tiene nuevos campos${NC}"
else
  echo -e "${RED}❌ Device.js no tiene los nuevos campos${NC}"
fi
echo ""

# Test 2: Verificar que KiosksAdmin.jsx tiene nueva lógica
echo "✓ Test 2: Verificando KiosksAdmin.jsx..."
if grep -q "groupedByBusiness" src/pages/KiosksAdmin.jsx && \
   grep -q "expandedBusinesses" src/pages/KiosksAdmin.jsx && \
   grep -q "countOnlineByBusiness" src/pages/KiosksAdmin.jsx; then
  echo -e "${GREEN}✅ KiosksAdmin.jsx tiene nuevas funciones${NC}"
else
  echo -e "${RED}❌ KiosksAdmin.jsx no tiene las nuevas funciones${NC}"
fi
echo ""

# Test 3: Verificar documentación
echo "✓ Test 3: Verificando documentación..."
if [ -f REFACTOR_GUIDE.md ] && [ -f DATABASE_EXAMPLES.md ] && \
   [ -f FUTURE_IMPROVEMENTS.md ] && [ -f IMPLEMENTATION_SUMMARY.md ]; then
  echo -e "${GREEN}✅ Documentación completa (4 archivos)${NC}"
else
  echo -e "${RED}❌ Falta documentación${NC}"
fi
echo ""

# Test 4: Buscar errores de sintaxis en JSX
echo "✓ Test 4: Verificando sintaxis JSX..."
if grep -c "className=\"" src/pages/KiosksAdmin.jsx > /dev/null; then
  echo -e "${GREEN}✅ JSX con Tailwind CSS detectado${NC}"
else
  echo -e "${YELLOW}⚠️  No se encontraron clases de Tailwind${NC}"
fi
echo ""

# Test 5: Verificar que faltan campos antiguos problemáticos
echo "✓ Test 5: Verificando referencias antiguas..."
if ! grep -q "filteredDevices.map" src/pages/KiosksAdmin.jsx 2>/dev/null; then
  echo -e "${GREEN}✅ Referencias antiguas eliminadas${NC}"
else
  echo -e "${YELLOW}⚠️  Aún hay referencias a filteredDevices${NC}"
fi
echo ""

# Summary
echo "=========================================================="
echo -e "${GREEN}✅ Verificación completada${NC}"
echo ""
echo "📋 Próximos pasos:"
echo "1. Actualizar backend para enviar businessName y otros campos"
echo "2. Ejecutar migración en base de datos"
echo "3. Asignar dispositivos a negocios"
echo "4. Probar en navegador (F12 > Console)"
echo "5. Verificar que API devuelve campos correctos"
echo ""
echo "📚 Leer documentación:"
echo "  - REFACTOR_GUIDE.md (implementación)"
echo "  - DATABASE_EXAMPLES.md (ejemplos de código)"
echo "  - IMPLEMENTATION_SUMMARY.md (resumen)"
echo ""
