"""
Task Scheduler for Indonesian Quantitative Trading Alert System
Manages daily signal generation, risk monitoring, and system maintenance tasks
"""

import asyncio
import logging
from typing import Dict, List, Callable, Any, Optional
from datetime import datetime, time, timedelta
import pytz
from dataclasses import dataclass
from enum import Enum
import croniter
from celery import Celery
from celery.schedules import crontab
import redis.asyncio as aioredis

from .config import settings
from .database import DatabaseManager
from .signal_service import SignalService
from .alert_engine import AlertEngine
from .risk_monitor import RiskMonitor

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Task type enumeration"""
    SIGNAL_GENERATION = "signal_generation"
    RISK_MONITORING = "risk_monitoring"
    DATA_COLLECTION = "data_collection"
    MODEL_RETRAINING = "model_retraining"
    PORTFOLIO_REBALANCING = "portfolio_rebalancing"
    SYSTEM_MAINTENANCE = "system_maintenance"
    BACKUP = "backup"
    REPORT_GENERATION = "report_generation"
    ALERT_CLEANUP = "alert_cleanup"


class TaskStatus(Enum):
    """Task status enumeration"""
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ScheduledTask:
    """Scheduled task definition"""
    task_id: str
    task_type: TaskType
    name: str
    cron_schedule: str
    timezone: str
    enabled: bool
    function: Callable
    args: List[Any]
    kwargs: Dict[str, Any]
    description: str
    max_retries: int = 3
    timeout_minutes: int = 60
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    status: TaskStatus = TaskStatus.SCHEDULED


class TaskExecutor:
    """Task execution engine"""

    def __init__(self, db_manager: DatabaseManager, redis_client):
        self.db_manager = db_manager
        self.redis_client = redis_client
        self.running_tasks: Dict[str, asyncio.Task] = {}

    async def execute_task(self, scheduled_task: ScheduledTask) -> Dict[str, Any]:
        """Execute a scheduled task"""
        task_id = scheduled_task.task_id
        start_time = datetime.now()

        try:
            logger.info(f"Starting task: {task_id} - {scheduled_task.name}")

            # Update task status
            scheduled_task.status = TaskStatus.RUNNING
            scheduled_task.last_run = start_time

            # Set timeout
            timeout = timedelta(minutes=scheduled_task.timeout_minutes)

            # Execute the task function
            result = await asyncio.wait_for(
                scheduled_task.function(*scheduled_task.args, **scheduled_task.kwargs),
                timeout=timeout.total_seconds()
            )

            # Task completed successfully
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()

            scheduled_task.status = TaskStatus.COMPLETED

            task_result = {
                'task_id': task_id,
                'status': 'completed',
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'execution_time_seconds': execution_time,
                'result': result
            }

            logger.info(f"Task completed: {task_id} in {execution_time:.2f} seconds")
            return task_result

        except asyncio.TimeoutError:
            scheduled_task.status = TaskStatus.FAILED
            error_msg = f"Task {task_id} timed out after {scheduled_task.timeout_minutes} minutes"
            logger.error(error_msg)

            return {
                'task_id': task_id,
                'status': 'failed',
                'start_time': start_time.isoformat(),
                'error': error_msg
            }

        except Exception as e:
            scheduled_task.status = TaskStatus.FAILED
            error_msg = f"Task {task_id} failed: {str(e)}"
            logger.error(error_msg)

            return {
                'task_id': task_id,
                'status': 'failed',
                'start_time': start_time.isoformat(),
                'error': error_msg
            }

        finally:
            # Clean up running task reference
            self.running_tasks.pop(task_id, None)

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task"""
        if task_id in self.running_tasks:
            task = self.running_tasks[task_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            return True
        return False


class TradingScheduler:
    """
    Main scheduler for the Indonesian trading system
    Manages all scheduled tasks including daily signal generation
    """

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.redis_client = None
        self.celery_app = None
        self.task_executor = None

        # Services
        self.signal_service = None
        self.alert_engine = None
        self.risk_monitor = None

        # Jakarta timezone
        self.jakarta_tz = pytz.timezone(settings.MARKET_TIMEZONE)

        # Scheduled tasks
        self.scheduled_tasks: Dict[str, ScheduledTask] = {}

        # Scheduler state
        self.is_running = False
        self.scheduler_task = None

    async def initialize(self):
        """Initialize the scheduler"""
        try:
            # Connect to Redis
            self.redis_client = await aioredis.from_url(
                settings.get_redis_url(),
                encoding="utf-8",
                decode_responses=True
            )

            # Initialize Celery for background tasks
            self.celery_app = Celery(
                'trading_scheduler',
                broker=settings.get_redis_url(),
                backend=settings.get_redis_url()
            )

            # Initialize task executor
            self.task_executor = TaskExecutor(self.db_manager, self.redis_client)

            # Initialize services
            self.signal_service = SignalService(self.db_manager)
            await self.signal_service.initialize()

            self.alert_engine = AlertEngine(self.db_manager)
            await self.alert_engine.initialize()

            self.risk_monitor = RiskMonitor(self.db_manager)
            await self.risk_monitor.initialize()

            # Register scheduled tasks
            await self._register_scheduled_tasks()

            logger.info("Trading scheduler initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize scheduler: {str(e)}")
            raise

    async def _register_scheduled_tasks(self):
        """Register all scheduled tasks"""

        # Daily signal generation (8:30 AM WIB)
        self.scheduled_tasks['daily_signals'] = ScheduledTask(
            task_id='daily_signals',
            task_type=TaskType.SIGNAL_GENERATION,
            name='Daily Signal Generation',
            cron_schedule='30 8 * * 1-5',  # 8:30 AM, Monday to Friday
            timezone=settings.MARKET_TIMEZONE,
            enabled=settings.AUTO_SIGNAL_GENERATION,
            function=self._generate_daily_signals,
            args=[],
            kwargs={},
            description='Generate daily trading signals before market open',
            timeout_minutes=30
        )

        # Risk monitoring (every 5 minutes during market hours)
        self.scheduled_tasks['risk_monitoring'] = ScheduledTask(
            task_id='risk_monitoring',
            task_type=TaskType.RISK_MONITORING,
            name='Risk Monitoring',
            cron_schedule='*/5 9-15 * * 1-5',  # Every 5 minutes, 9 AM to 3 PM, Monday to Friday
            timezone=settings.MARKET_TIMEZONE,
            enabled=True,
            function=self._perform_risk_check,
            args=[],
            kwargs={},
            description='Monitor portfolio risk during market hours',
            timeout_minutes=5
        )

        # Weekly model retraining (Sunday 8 PM WIB)
        self.scheduled_tasks['model_retrain'] = ScheduledTask(
            task_id='model_retrain',
            task_type=TaskType.MODEL_RETRAINING,
            name='Weekly Model Retraining',
            cron_schedule='0 20 * * 0',  # 8 PM Sunday
            timezone=settings.MARKET_TIMEZONE,
            enabled=settings.AUTO_RETRAIN_ENABLED,
            function=self._retrain_models,
            args=[],
            kwargs={},
            description='Retrain ML models with latest data',
            timeout_minutes=180  # 3 hours
        )

        # Daily backup (2 AM WIB)
        self.scheduled_tasks['daily_backup'] = ScheduledTask(
            task_id='daily_backup',
            task_type=TaskType.BACKUP,
            name='Daily Backup',
            cron_schedule='0 2 * * *',  # 2 AM daily
            timezone=settings.MARKET_TIMEZONE,
            enabled=settings.BACKUP_ENABLED,
            function=self._perform_backup,
            args=[],
            kwargs={},
            description='Create daily database and file backups',
            timeout_minutes=60
        )

        # Daily report generation (6 PM WIB)
        self.scheduled_tasks['daily_report'] = ScheduledTask(
            task_id='daily_report',
            task_type=TaskType.REPORT_GENERATION,
            name='Daily Report Generation',
            cron_schedule='0 18 * * 1-5',  # 6 PM, Monday to Friday
            timezone=settings.MARKET_TIMEZONE,
            enabled=True,
            function=self._generate_daily_report,
            args=[],
            kwargs={},
            description='Generate and distribute daily trading reports',
            timeout_minutes=15
        )

        # Alert cleanup (midnight WIB)
        self.scheduled_tasks['alert_cleanup'] = ScheduledTask(
            task_id='alert_cleanup',
            task_type=TaskType.ALERT_CLEANUP,
            name='Alert Cleanup',
            cron_schedule='0 0 * * *',  # Midnight daily
            timezone=settings.MARKET_TIMEZONE,
            enabled=True,
            function=self._cleanup_old_alerts,
            args=[],
            kwargs={},
            description='Clean up old and expired alerts',
            timeout_minutes=10
        )

        # System maintenance (3 AM Sunday WIB)
        self.scheduled_tasks['system_maintenance'] = ScheduledTask(
            task_id='system_maintenance',
            task_type=TaskType.SYSTEM_MAINTENANCE,
            name='System Maintenance',
            cron_schedule='0 3 * * 0',  # 3 AM Sunday
            timezone=settings.MARKET_TIMEZONE,
            enabled=True,
            function=self._perform_maintenance,
            args=[],
            kwargs={},
            description='Perform system maintenance and optimization',
            timeout_minutes=120  # 2 hours
        )

        # Calculate next run times
        for task in self.scheduled_tasks.values():
            task.next_run = self._calculate_next_run(task)

        logger.info(f"Registered {len(self.scheduled_tasks)} scheduled tasks")

    def _calculate_next_run(self, task: ScheduledTask) -> datetime:
        """Calculate next run time for a task"""
        try:
            tz = pytz.timezone(task.timezone)
            now = datetime.now(tz)
            cron = croniter.croniter(task.cron_schedule, now)
            return cron.get_next(datetime)
        except Exception as e:
            logger.error(f"Error calculating next run for task {task.task_id}: {str(e)}")
            return datetime.now(self.jakarta_tz) + timedelta(hours=24)

    async def start_scheduler(self):
        """Start the task scheduler"""
        if self.is_running:
            logger.warning("Scheduler already running")
            return

        self.is_running = True
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Task scheduler started")

    async def stop_scheduler(self):
        """Stop the task scheduler"""
        self.is_running = False

        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass

        # Cancel all running tasks
        for task_id in list(self.task_executor.running_tasks.keys()):
            await self.task_executor.cancel_task(task_id)

        logger.info("Task scheduler stopped")

    async def _scheduler_loop(self):
        """Main scheduler loop"""
        while self.is_running:
            try:
                current_time = datetime.now(self.jakarta_tz)

                # Check for tasks that need to run
                for task in self.scheduled_tasks.values():
                    if (task.enabled and
                        task.next_run and
                        current_time >= task.next_run and
                        task.status != TaskStatus.RUNNING and
                        task.task_id not in self.task_executor.running_tasks):

                        # Start the task
                        asyncio.create_task(self._run_scheduled_task(task))

                # Sleep for 1 minute before checking again
                await asyncio.sleep(60)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {str(e)}")
                await asyncio.sleep(60)

    async def _run_scheduled_task(self, task: ScheduledTask):
        """Run a scheduled task"""
        try:
            # Add to running tasks
            execution_task = asyncio.create_task(
                self.task_executor.execute_task(task)
            )
            self.task_executor.running_tasks[task.task_id] = execution_task

            # Execute the task
            result = await execution_task

            # Log result
            if result['status'] == 'completed':
                logger.info(f"Scheduled task completed: {task.task_id}")
            else:
                logger.error(f"Scheduled task failed: {task.task_id} - {result.get('error')}")

            # Calculate next run time
            task.next_run = self._calculate_next_run(task)

            # Save task execution record
            await self._save_task_execution(task, result)

        except Exception as e:
            logger.error(f"Error running scheduled task {task.task_id}: {str(e)}")
            task.status = TaskStatus.FAILED
            task.next_run = self._calculate_next_run(task)

    async def _save_task_execution(self, task: ScheduledTask, result: Dict[str, Any]):
        """Save task execution record to database"""
        try:
            execution_record = {
                'task_id': task.task_id,
                'task_type': task.task_type.value,
                'status': result['status'],
                'start_time': result['start_time'],
                'end_time': result.get('end_time'),
                'execution_time_seconds': result.get('execution_time_seconds'),
                'error_message': result.get('error'),
                'result_data': result.get('result', {})
            }

            # This would save to a task_executions table
            # await self.db_manager.save_task_execution(execution_record)

        except Exception as e:
            logger.error(f"Error saving task execution record: {str(e)}")

    # Task implementation methods
    async def _generate_daily_signals(self) -> Dict[str, Any]:
        """Generate daily trading signals"""
        try:
            task_id = await self.signal_service.start_signal_generation()

            # Wait for completion (with timeout)
            max_wait = 20 * 60  # 20 minutes
            wait_interval = 30  # 30 seconds
            total_waited = 0

            while total_waited < max_wait:
                status = await self.signal_service.get_generation_status(task_id)

                if status['status'] in ['completed', 'failed']:
                    return {
                        'task_id': task_id,
                        'status': status['status'],
                        'signals_generated': status.get('signals_generated', 0),
                        'execution_time': total_waited
                    }

                await asyncio.sleep(wait_interval)
                total_waited += wait_interval

            return {
                'task_id': task_id,
                'status': 'timeout',
                'error': 'Signal generation timed out'
            }

        except Exception as e:
            logger.error(f"Error in signal generation task: {str(e)}")
            return {'status': 'failed', 'error': str(e)}

    async def _perform_risk_check(self) -> Dict[str, Any]:
        """Perform risk monitoring check"""
        try:
            result = await self.risk_monitor.force_risk_check()
            return result

        except Exception as e:
            logger.error(f"Error in risk monitoring task: {str(e)}")
            return {'status': 'failed', 'error': str(e)}

    async def _retrain_models(self) -> Dict[str, Any]:
        """Retrain ML models"""
        try:
            # This would implement model retraining logic
            # For now, return a placeholder
            return {
                'status': 'completed',
                'message': 'Model retraining not yet implemented',
                'models_retrained': 0
            }

        except Exception as e:
            logger.error(f"Error in model retraining task: {str(e)}")
            return {'status': 'failed', 'error': str(e)}

    async def _perform_backup(self) -> Dict[str, Any]:
        """Perform system backup"""
        try:
            # This would implement backup logic
            return {
                'status': 'completed',
                'message': 'System backup not yet implemented',
                'backup_size_mb': 0
            }

        except Exception as e:
            logger.error(f"Error in backup task: {str(e)}")
            return {'status': 'failed', 'error': str(e)}

    async def _generate_daily_report(self) -> Dict[str, Any]:
        """Generate daily trading report"""
        try:
            today = datetime.now(self.jakarta_tz).date()
            report = await self.signal_service.generate_daily_report(today)

            return {
                'status': 'completed',
                'report_date': today.isoformat(),
                'report_data': report
            }

        except Exception as e:
            logger.error(f"Error in daily report generation: {str(e)}")
            return {'status': 'failed', 'error': str(e)}

    async def _cleanup_old_alerts(self) -> Dict[str, Any]:
        """Clean up old alerts"""
        try:
            # This would implement alert cleanup logic
            cutoff_date = datetime.now(self.jakarta_tz) - timedelta(days=30)

            return {
                'status': 'completed',
                'message': 'Alert cleanup not yet implemented',
                'alerts_cleaned': 0,
                'cutoff_date': cutoff_date.isoformat()
            }

        except Exception as e:
            logger.error(f"Error in alert cleanup task: {str(e)}")
            return {'status': 'failed', 'error': str(e)}

    async def _perform_maintenance(self) -> Dict[str, Any]:
        """Perform system maintenance"""
        try:
            # This would implement maintenance tasks like:
            # - Database optimization
            # - Cache cleanup
            # - Log rotation
            # - Performance monitoring

            return {
                'status': 'completed',
                'message': 'System maintenance not yet implemented',
                'maintenance_tasks_completed': 0
            }

        except Exception as e:
            logger.error(f"Error in system maintenance task: {str(e)}")
            return {'status': 'failed', 'error': str(e)}

    # Public methods
    async def get_scheduled_tasks(self) -> List[Dict[str, Any]]:
        """Get list of all scheduled tasks"""
        tasks = []
        for task in self.scheduled_tasks.values():
            tasks.append({
                'task_id': task.task_id,
                'name': task.name,
                'task_type': task.task_type.value,
                'cron_schedule': task.cron_schedule,
                'enabled': task.enabled,
                'status': task.status.value,
                'last_run': task.last_run.isoformat() if task.last_run else None,
                'next_run': task.next_run.isoformat() if task.next_run else None,
                'description': task.description
            })
        return tasks

    async def enable_task(self, task_id: str) -> bool:
        """Enable a scheduled task"""
        if task_id in self.scheduled_tasks:
            self.scheduled_tasks[task_id].enabled = True
            self.scheduled_tasks[task_id].next_run = self._calculate_next_run(
                self.scheduled_tasks[task_id]
            )
            logger.info(f"Task enabled: {task_id}")
            return True
        return False

    async def disable_task(self, task_id: str) -> bool:
        """Disable a scheduled task"""
        if task_id in self.scheduled_tasks:
            self.scheduled_tasks[task_id].enabled = False
            logger.info(f"Task disabled: {task_id}")
            return True
        return False

    async def run_task_now(self, task_id: str) -> Dict[str, Any]:
        """Run a task immediately"""
        if task_id not in self.scheduled_tasks:
            return {'status': 'failed', 'error': f'Task {task_id} not found'}

        task = self.scheduled_tasks[task_id]

        if task.task_id in self.task_executor.running_tasks:
            return {'status': 'failed', 'error': f'Task {task_id} is already running'}

        # Run the task
        try:
            result = await self.task_executor.execute_task(task)
            return result
        except Exception as e:
            return {'status': 'failed', 'error': str(e)}

    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get status of a specific task"""
        if task_id not in self.scheduled_tasks:
            return {'error': f'Task {task_id} not found'}

        task = self.scheduled_tasks[task_id]
        is_running = task.task_id in self.task_executor.running_tasks

        return {
            'task_id': task.task_id,
            'name': task.name,
            'status': task.status.value,
            'is_running': is_running,
            'enabled': task.enabled,
            'last_run': task.last_run.isoformat() if task.last_run else None,
            'next_run': task.next_run.isoformat() if task.next_run else None,
            'description': task.description
        }

    async def health_check(self) -> Dict[str, Any]:
        """Health check for scheduler"""
        running_tasks = len(self.task_executor.running_tasks)
        enabled_tasks = len([t for t in self.scheduled_tasks.values() if t.enabled])

        return {
            'service': 'scheduler',
            'status': 'healthy' if self.is_running else 'stopped',
            'total_tasks': len(self.scheduled_tasks),
            'enabled_tasks': enabled_tasks,
            'running_tasks': running_tasks,
            'redis_connected': self.redis_client is not None
        }