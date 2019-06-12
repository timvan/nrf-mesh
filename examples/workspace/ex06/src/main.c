
#include "boards.h"
#include "log.h"

#include "mesh_app_utils.h"

#include "ble_softdevice_support.h"

#include "app_timer.h"

#include "nrfx_gpiote.h"

#define PIN_IN 25

static void in_pin_handler(nrfx_gpiote_pin_t pin, nrf_gpiote_polarity_t action)
{
    __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "shit happened %d\n", action);
}

static void initialize(void)
{
    __LOG_INIT(LOG_MSK_DEFAULT | LOG_SRC_ACCESS | LOG_SRC_SERIAL | LOG_SRC_APP, LOG_LEVEL_INFO, log_callback_rtt);
    __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "----- Ex06 GPIOTE Interupts  -----\n");

    ERROR_CHECK(app_timer_init());


    // ble_stack_init();

    nrfx_gpiote_init();

    nrfx_gpiote_in_config_t in_config = NRFX_GPIOTE_CONFIG_IN_SENSE_TOGGLE(true);
    in_config.pull = NRF_GPIO_PIN_PULLDOWN;

    nrfx_gpiote_in_init(PIN_IN, &in_config, in_pin_handler);

    nrfx_gpiote_in_event_enable(PIN_IN, true);

    __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "Initialization complete!\n");
}

int main(void)
{
    initialize();

    for (;;)
    {
        (void)sd_app_evt_wait();
    }
}
