class StandardRouter:
    """A basic router base class."""

    route_app_labels = NotImplemented
    db_name = NotImplemented

    def db_for_read(self, model, **hints):
        """Attempts to read nell models go to nell."""
        if model._meta.app_label in self.route_app_labels:
            return self.db_name
        return None

    def db_for_write(self, model, **hints):
        """Attempts to write nell models go to gbtarchive."""
        if model._meta.app_label in self.route_app_labels:
            return self.db_name
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """Allow relations if a model in one of our apps is involved."""
        if (
            obj1._meta.app_label in self.route_app_labels
            or obj2._meta.app_label in self.route_app_labels
        ):
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):

        if app_label in self.route_app_labels:
            return db == self.db_name
        return None


class LegacyRfiRouter(StandardRouter):
    """A router to control all database operations on models in the legacy_rfi app"""

    route_app_labels = {"legacy_rfi"}
    db_name = "legacy_rfi"
