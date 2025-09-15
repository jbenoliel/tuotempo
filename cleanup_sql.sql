-- Script de limpieza para call_schedule en Railway
-- Ejecutar estas consultas una por una

-- 1. Contar registros iniciales
SELECT 'ESTADO INICIAL' as status;
SELECT COUNT(*) as total_registros FROM call_schedule;
SELECT COUNT(*) as registros_cancelled FROM call_schedule WHERE status = 'cancelled';
SELECT COUNT(*) as registros_pending FROM call_schedule WHERE status = 'pending';

-- 2. Cancelar programaciones de leads cerrados
SELECT 'CANCELANDO PROGRAMACIONES DE LEADS CERRADOS' as status;
UPDATE call_schedule cs
JOIN leads l ON cs.lead_id = l.id
SET cs.status = 'cancelled',
    cs.updated_at = NOW()
WHERE l.lead_status = 'closed'
AND cs.status = 'pending';

-- 3. Eliminar programaciones duplicadas canceladas del mismo día
SELECT 'ELIMINANDO DUPLICADAS CANCELLED' as status;
DELETE cs1 FROM call_schedule cs1
INNER JOIN call_schedule cs2
WHERE cs1.id < cs2.id
AND cs1.lead_id = cs2.lead_id
AND cs1.status = 'cancelled'
AND cs2.status = 'cancelled'
AND DATE(cs1.created_at) = DATE(cs2.created_at);

-- 4. Eliminar programaciones cancelled muy antiguas (más de 7 días)
SELECT 'ELIMINANDO CANCELLED ANTIGUOS' as status;
DELETE FROM call_schedule
WHERE status = 'cancelled'
AND updated_at < DATE_SUB(NOW(), INTERVAL 7 DAY);

-- 5. Limpiar programaciones huérfanas
SELECT 'LIMPIANDO HUERFANAS' as status;
DELETE cs FROM call_schedule cs
LEFT JOIN leads l ON cs.lead_id = l.id
WHERE l.id IS NULL;

-- 6. Verificar leads con múltiples programaciones pendientes
SELECT 'LEADS CON MULTIPLES PENDIENTES' as status;
SELECT lead_id, COUNT(*) as count
FROM call_schedule
WHERE status = 'pending'
GROUP BY lead_id
HAVING count > 1
ORDER BY count DESC
LIMIT 10;

-- 7. Mantener solo la programación más reciente por lead
SELECT 'ELIMINANDO PENDIENTES DUPLICADAS' as status;
DELETE cs1 FROM call_schedule cs1
INNER JOIN (
    SELECT lead_id, MAX(id) as max_id
    FROM call_schedule
    WHERE status = 'pending'
    GROUP BY lead_id
    HAVING COUNT(*) > 1
) cs2 ON cs1.lead_id = cs2.lead_id
WHERE cs1.status = 'pending'
AND cs1.id != cs2.max_id;

-- 8. Estado final
SELECT 'ESTADO FINAL' as status;
SELECT COUNT(*) as total_registros FROM call_schedule;
SELECT COUNT(*) as registros_cancelled FROM call_schedule WHERE status = 'cancelled';
SELECT COUNT(*) as registros_pending FROM call_schedule WHERE status = 'pending';

-- 9. Verificar leads problemáticos específicos
SELECT 'VERIFICACION LEADS PROBLEMATICOS' as status;
SELECT cs.lead_id,
       COUNT(*) as total_schedules,
       SUM(CASE WHEN cs.status = 'pending' THEN 1 ELSE 0 END) as pending,
       SUM(CASE WHEN cs.status = 'cancelled' THEN 1 ELSE 0 END) as cancelled,
       l.lead_status
FROM call_schedule cs
LEFT JOIN leads l ON cs.lead_id = l.id
WHERE cs.lead_id IN (556, 558, 561, 562, 564, 563, 551, 566, 568, 565, 570, 572, 567, 549, 571, 574, 575, 573, 569, 2052, 2085, 2340, 2467)
GROUP BY cs.lead_id, l.lead_status
ORDER BY total_schedules DESC;