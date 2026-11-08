from app.auth import ROLE_ADMIN, ROLE_MANAGER, ROLE_TEACHER


ROLE_RESOURCES = {
    ROLE_ADMIN: {
        "dashboard",
        "banners",
        "campuses",
        "staff",
        "articles",
        "materials",
        "leads",
        "students",
        "visits",
    },
    ROLE_MANAGER: {"dashboard", "staff", "students", "visits"},
    ROLE_TEACHER: {"dashboard", "students", "visits"},
}


def can_access_resource(role: str, resource: str) -> bool:
    return resource in ROLE_RESOURCES.get(role, set())


def menu_resources(role: str) -> tuple[str, ...]:
    ordered = (
        "dashboard",
        "campuses",
        "staff",
        "articles",
        "materials",
        "leads",
        "students",
        "visits",
    )
    return tuple(resource for resource in ordered if can_access_resource(role, resource))
