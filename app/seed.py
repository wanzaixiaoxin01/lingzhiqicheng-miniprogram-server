from app import models
from app.db import SessionLocal, init_db


INTEREST_ACTIVITY_SEED = [
    {
        "id": "interest-programming",
        "title": "编程与逻辑",
        "category": "编程与逻辑",
        "cover_url": "/static/courses/programming-workshop-v1.jpg",
        "summary": "从积木编程到项目实践，培养拆解问题和创造性解决问题的能力。",
        "suitable_grade": "小学 / 初中",
        "service_period": "按主题活动安排",
        "price_text": "预约咨询",
        "tags": ["编程思维", "逻辑训练"],
        "content": "通过可视化编程、任务挑战和项目实践，帮助孩子建立清晰的逻辑表达和解决问题的方法。",
        "sort_order": 1,
        "status": "published",
    },
    {
        "id": "interest-english-speaking",
        "title": "英语口语",
        "category": "英语口语",
        "cover_url": "/static/courses/english-speaking-v1.jpg",
        "summary": "通过智能设备与真实情境互动，让孩子愿意开口、能够表达。",
        "suitable_grade": "小学 / 初中",
        "service_period": "按主题活动安排",
        "price_text": "预约咨询",
        "tags": ["设备互动", "情境表达"],
        "content": "结合智能设备和情境互动，让孩子在真实场景中体验语言表达的乐趣。",
        "sort_order": 2,
        "status": "published",
    },
    {
        "id": "interest-expression-reading",
        "title": "表达与阅读",
        "category": "表达与阅读",
        "cover_url": "/static/courses/expression-reading-v1.jpg",
        "summary": "拓展阅读丰富度，鼓励孩子思考、讨论并勇敢表达自己的观点。",
        "suitable_grade": "小学 / 初中",
        "service_period": "按主题活动安排",
        "price_text": "预约咨询",
        "tags": ["阅读积累", "观点表达"],
        "content": "通过丰富的阅读材料、讨论和分享，培养孩子的理解力、思考力与表达力。",
        "sort_order": 3,
        "status": "published",
    },
    {
        "id": "interest-calligraphy",
        "title": "练字",
        "category": "练字",
        "cover_url": "/static/courses/handwriting-v1.jpg",
        "summary": "从基本笔画到作品练习，在专注书写中建立审美和耐心。",
        "suitable_grade": "小学 / 初中",
        "service_period": "按主题活动安排",
        "price_text": "预约咨询",
        "tags": ["硬笔基础", "审美培养"],
        "content": "从坐姿、握笔和基本笔画入手，逐步建立规范书写习惯和对汉字之美的感受。",
        "sort_order": 4,
        "status": "published",
    },
    {
        "id": "interest-painting",
        "title": "绘画",
        "category": "绘画",
        "cover_url": "/static/courses/painting-v1.jpg",
        "summary": "从观察和想象出发，用画笔把自己的感受变成作品。",
        "suitable_grade": "小学 / 初中",
        "service_period": "按主题活动安排",
        "price_text": "预约咨询",
        "tags": ["观察力", "想象表达"],
        "content": "通过主题创作、色彩练习和作品分享，鼓励孩子观察生活、表达感受并建立审美自信。",
        "sort_order": 5,
        "status": "published",
    },
    {
        "id": "interest-music-instruments",
        "title": "音乐与乐器",
        "category": "音乐与乐器",
        "cover_url": "/static/courses/music-instruments-v1.jpg",
        "summary": "体验钢琴、吉他等乐器，在节奏与演奏中发现自己的兴趣。",
        "suitable_grade": "小学 / 初中",
        "service_period": "按主题活动安排",
        "price_text": "预约咨询",
        "tags": ["钢琴", "吉他", "节奏体验"],
        "content": "通过钢琴、吉他等乐器体验，帮助孩子感受节奏、发现兴趣并获得舞台表达的机会。",
        "sort_order": 6,
        "status": "published",
    },
]

LEGACY_COURSE_CATEGORIES = {"智习室", "晚托"}


def seed_courses(db) -> None:
    for values in INTEREST_ACTIVITY_SEED:
        if db.get(models.Course, values["id"]) is None:
            db.add(models.Course(**values))

    for course in db.query(models.Course).all():
        if course.category in LEGACY_COURSE_CATEGORIES:
            course.status = "hidden"


def seed() -> None:
    init_db()
    db = SessionLocal()
    try:
        if db.query(models.Banner).count() == 0:
            db.add(
                models.Banner(
                    title="AI 智慧教育服务品牌",
                    image_url="/static/logo.png",
                    link_type="appointment",
                    link_value="/pages/appointment/index",
                    sort_order=1,
                    status="published",
                )
            )

        if db.query(models.Campus).count() == 0:
            db.add(
                models.Campus(
                    name="灵智启程智习室",
                    cover_url="/static/logo.png",
                    address="请在后台填写校区详细地址",
                    phone="请在后台填写联系电话",
                    business_hours="周一至周日 09:00-21:00",
                    intro="提供安静自习场地、智能设备展示和预约到店体验服务。",
                    status="published",
                )
            )

        seed_courses(db)

        if db.query(models.Article).count() == 0:
            db.add_all(
                [
                    models.Article(
                        type="material",
                        title="空间开放安排公告",
                        cover_url="/static/logo.png",
                        summary="空间公告：查看开放时间与到店须知。",
                        content="请家长提前查看空间开放时间和到店须知，如有调整将通过空间公告更新。",
                        sort_order=1,
                        status="published",
                    ),
                    models.Article(
                        type="news",
                        title="灵智启程智习室服务介绍",
                        cover_url="/static/logo.png",
                        summary="了解智习室、智能设备和预约到店体验服务。",
                        content="灵智启程提供自习场地、智能设备展示、配置咨询和到店体验服务。",
                        sort_order=2,
                        status="published",
                    ),
                    models.Article(
                        type="activity",
                        title="校区开放日预约",
                        cover_url="/static/logo.png",
                        summary="欢迎家长预约到店参观体验。",
                        content="校区开放日支持环境参观、服务介绍和学习方案咨询。",
                        sort_order=3,
                        status="published",
                    ),
                ]
            )

        if db.get(models.Setting, "service_phone") is None:
            db.add(models.Setting(key="service_phone", value={"text": "请在后台配置客服电话"}))
        if db.get(models.Setting, "learning_machine_posters") is None:
            db.add(models.Setting(key="learning_machine_posters", value={"posters": []}))

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
