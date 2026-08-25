from modules.extraction import find_tables
from modules.validation import validate_data
from modules.transformation import transform_data
from modules.load import load_data
from modules.logs import (
    get_logger,
    log_start,
    log_end,
    log_extraction,
    log_validation,
    log_transformation,
    log_error
)


def main():

    logger = get_logger()

    log_start(logger)

    TABLES = {
    "tb_user",
    "tb_last_water_bill",
    "tb_user_habit",
    "tb_user_habit_day",
    "tb_address",
    "tb_property",
    "tb_user_property",
    "tb_region_rate",
    "tb_device"
    }

    

    try:

        # 1. EXTRAÇÃO
        data = find_tables(TABLES)

        for table, dataframe in data.items():

            log_extraction(
                logger,
                table,
                len(dataframe)
            )

        # 2. VALIDAÇÃO
        validation_result = validate_data(
            data
        )

        valid_data = validation_result["valid"]
        errors = validation_result["errors"]

        for table, dataframe in valid_data.items():

            table_errors = errors.get(
                table
            )

            error_quantity = (
                len(table_errors)
                if table_errors is not None
                else 0
            )

            log_validation(
                logger,
                table,
                len(dataframe),
                error_quantity
            )


        # 3. TRANSFORMAÇÃO
        transformed_data = transform_data(
            valid_data
        )

        for table, dataframe in transformed_data.items():

            log_transformation(
                logger,
                table,
                len(dataframe)
            )


        # 4. CARGA
        load_data(
            transformed_data,
        )


        # 5. FINALIZAÇÃO
        log_end(logger)


    except Exception as exception:

        log_error(
            logger,
            "Erro durante a execução do RPA",
            exception
        )

        raise


if __name__ == "__main__":
    main()