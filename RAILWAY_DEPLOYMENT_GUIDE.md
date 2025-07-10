# 🚄 GUÍA DE DESPLIEGUE EN RAILWAY

## 📋 **ANTES DE DESPLEGAR**

### **1. 🔧 Configurar Variables de Entorno en Railway**

Ve a tu proyecto en Railway → Settings → Variables y añade:

```bash
# Pearl AI - Credenciales de Producción
PEARL_ACCOUNT_ID=tu_account_id_real
PEARL_SECRET_KEY=tu_secret_key_real  
PEARL_API_URL=https://api.nlpearl.ai/v1
PEARL_OUTBOUND_ID=tu_outbound_id_produccion

# Flask - Configuración de Producción
SECRET_KEY=genera_una_clave_super_segura_aqui
DEBUG=False
```

### **2. 📊 Ejecutar Migración en Railway**

**Opción A: Desde tu máquina local**
```bash
# Asegúrate de que tu .env tenga las credenciales de Railway
python railway_migration.py
```

**Opción B: Desde Railway Console**
```bash
# En Railway Console ejecuta:
python db_migration_add_call_fields.py
```

### **3. ✅ Verificar Entorno**
```bash
python check_railway_env.py
```

---

## 🚀 **DESPLIEGUE PASO A PASO**

### **Paso 1: Commit y Push**
```bash
git add .
git commit -m "feat: Sistema de llamadas automáticas con Pearl AI"
git push origin main
```

### **Paso 2: Railway Auto-Deploy**
- Railway detectará los cambios automáticamente
- Monitorizará el despliegue en Railway Dashboard
- Verificará que no hay errores en los logs

### **Paso 3: Verificación Post-Despliegue**
```bash
# Prueba estos endpoints en tu URL de Railway:
https://tu-app.up.railway.app/calls
https://tu-app.up.railway.app/api/calls/status
https://tu-app.up.railway.app/api/calls/test/connection
```

---

## 🔧 **POSIBLES PROBLEMAS Y SOLUCIONES**

### **❌ Error: "No module named 'pearl_caller'"**
**Solución:** Verifica que todos los archivos estén en el repositorio
```bash
git status
git add pearl_caller.py call_manager.py api_pearl_calls.py
git commit -m "fix: Add missing Pearl AI modules"
git push
```

### **❌ Error: "Static files not found"**
**Solución:** Verificar estructura de archivos estáticos
```
static/
├── css/
│   └── calls_manager.css
└── calls_manager.js  # ⚠️ Debería estar en static/js/
```

**Corrección:**
```bash
mkdir -p static/js
mv static/calls_manager.js static/js/calls_manager.js
```

### **❌ Error: "Pearl AI Connection Failed"**
**Solución:** Verificar credenciales en Railway Variables
1. Ve a Railway → Settings → Variables
2. Verifica PEARL_ACCOUNT_ID y PEARL_SECRET_KEY
3. Prueba conexión: `/api/calls/test/connection`

### **❌ Error: "Database connection failed"**
**Solución:** Verificar migración
```bash
python railway_migration.py
```

---

## 📊 **VERIFICACIÓN COMPLETA**

### **1. ✅ URLs que deben funcionar:**
```
✅ https://tu-app.up.railway.app/calls
✅ https://tu-app.up.railway.app/api/calls/status  
✅ https://tu-app.up.railway.app/api/calls/test/connection
✅ https://tu-app.up.railway.app/api/calls/leads
```

### **2. ✅ Funcionalidades que deben trabajar:**
- [ ] Login al dashboard
- [ ] Click en "Iniciar Llamadas" desde dashboard
- [ ] Carga de tabla de leads con filtros
- [ ] Selección de leads con checkboxes
- [ ] Test de conexión Pearl AI exitoso
- [ ] Botón START inicia llamadas (con credenciales reales)
- [ ] Estadísticas en tiempo real
- [ ] Botón STOP detiene llamadas

### **3. ✅ Base de datos debe tener:**
```sql
-- Verificar en Railway Database:
DESCRIBE leads;
-- Debe mostrar los nuevos campos:
-- call_status, call_priority, selected_for_calling, etc.
```

---

## 🎯 **CHECKLIST DE PRODUCCIÓN**

### **Antes del Despliegue:**
- [ ] Variables de entorno configuradas en Railway
- [ ] Credenciales Pearl AI válidas 
- [ ] Migración ejecutada exitosamente
- [ ] Archivos estáticos en ubicaciones correctas
- [ ] Verificación de entorno pasada

### **Después del Despliegue:**
- [ ] URL /calls carga correctamente
- [ ] API endpoints responden
- [ ] Conexión Pearl AI exitosa
- [ ] Tabla de leads muestra nuevos campos
- [ ] Botones START/STOP funcionan
- [ ] Estadísticas se actualizan en tiempo real

---

## 🚨 **IMPORTANTE PARA PRODUCCIÓN**

### **🔐 Seguridad:**
- ✅ `DEBUG=False` en Railway
- ✅ `SECRET_KEY` fuerte y único
- ✅ Credenciales Pearl AI seguras
- ✅ Base de datos con SSL/TLS

### **📊 Monitoreo:**
- ✅ Logs de Railway para errores
- ✅ Métricas de uso de Pearl AI
- ✅ Estadísticas de llamadas en dashboard
- ✅ Performance de base de datos

### **🔄 Backup:**
- ✅ Backup de base de datos antes de usar en producción
- ✅ Plan de rollback si algo falla
- ✅ Variables de entorno documentadas

---

## 📞 **SOPORTE**

Si encuentras problemas:

1. **Revisa logs de Railway** en Dashboard → Deployments → View Logs
2. **Verifica variables** en Settings → Variables
3. **Prueba endpoints** individualmente
4. **Consulta documentación Pearl AI** para credenciales

**¡Tu sistema de llamadas automáticas está listo para producción! 🎉**
